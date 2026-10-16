"""Create and locally verify a Mac App Store package from the canonical app."""
from pathlib import Path, PurePosixPath
import argparse
import datetime
import hashlib
import gzip
import json
import os
import plistlib
import re
import ssl
import struct
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET


APP_IDENTIFIER = "com.iisacc.Alright"
EXTENSION_IDENTIFIER = APP_IDENTIFIER + ".FinderSync"
INSTALLER_PREFIX = "3rd Party Mac Developer Installer: "
APPLICATION_PREFIXES = ("Apple Distribution: ", "3rd Party Mac Developer Application: ")
INSTALLER_MARKER = "1.2.840.113635.100.6.1.8"
INSTALLER_EKU = "1.2.840.113635.100.4.9"
APPLICATION_MARKER = "1.2.840.113635.100.6.1.7"
QUARANTINE_ATTRIBUTE = "com.apple.quarantine"


class PackagingError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise PackagingError(message)


def run(command, *, env, input=None):
    """Capture tool output; failures never print keychain or certificate contents."""
    try:
        result = subprocess.run(command, input=input, capture_output=True, env=env)
    except OSError as error:
        raise PackagingError(f"Cannot run {Path(command[0]).name}: {error.strerror}") from error
    require(result.returncode == 0,
            f"{Path(command[0]).name} {command[1]} failed (exit {result.returncode}).")
    return result


def sanitize_bundle_quarantine(app, *, env):
    """Remove only quarantine from build artifacts, never following symlinks."""
    require(not app.is_symlink(), "The canonical application must not be a symbolic link.")

    def traversal_error(error):
        raise error

    paths = [app]
    for directory, directories, files in os.walk(app, followlinks=False, onerror=traversal_error):
        paths.extend(Path(directory) / name for name in sorted(directories + files))
    removed = 0
    for path in paths:
        # -s applies to the symlink itself. Its target may be outside build/.
        before = set(run(["/usr/bin/xattr", "-s", str(path)], env=env).stdout.decode().splitlines())
        if QUARANTINE_ATTRIBUTE in before:
            run(["/usr/bin/xattr", "-d", "-s", QUARANTINE_ATTRIBUTE, str(path)], env=env)
            removed += 1
        after = set(run(["/usr/bin/xattr", "-s", str(path)], env=env).stdout.decode().splitlines())
        require(QUARANTINE_ATTRIBUTE not in after, f"The quarantine attribute remains on bundle entry {path}.")
        require(after == before - {QUARANTINE_ATTRIBUTE},
                f"Quarantine sanitization changed unrelated extended attributes on {path}.")
    return {"attribute": QUARANTINE_ATTRIBUTE, "removed_count": removed,
            "inspected_count": len(paths), "verified_absent": True}


def appledouble_attribute_names(data):
    """Read Apple's copyfile AppleDouble ATTR table without exposing values."""
    require(len(data) >= 26 and struct.unpack_from(">II", data) == (0x00051607, 0x00020000),
            "Malformed AppleDouble payload metadata.")
    count = struct.unpack_from(">H", data, 24)[0]
    require(26 + count * 12 <= len(data), "Truncated AppleDouble entry table.")
    names = set()
    for index in range(count):
        kind, offset, length = struct.unpack_from(">III", data, 26 + index * 12)
        require(offset >= 26 + count * 12 and offset + length <= len(data), "Invalid AppleDouble entry bounds.")
        if kind != 9 or length <= 34:
            continue
        # FinderInfo (32 bytes) and two padding bytes precede the ATTR header.
        attribute_offset = offset + 34
        require(length >= 34 + 36, "Truncated AppleDouble attribute header.")
        fields = struct.unpack_from(">8I2H", data, attribute_offset)
        magic, total, data_start, data_length, attribute_count = fields[0], fields[2], fields[3], fields[4], fields[9]
        require(magic == 0x41545452 and attribute_offset + 36 <= data_start <= total <= len(data)
                and data_start + data_length <= total, "Invalid AppleDouble attribute table bounds.")
        position = attribute_offset + 36
        for attribute in range(attribute_count):
            require(position + 11 <= data_start, "Truncated AppleDouble attribute entry.")
            value_offset, value_length, flags, name_length = struct.unpack_from(">IIHB", data, position)
            require(name_length > 0 and position + 11 + name_length <= data_start
                    and data_start <= value_offset and value_offset + value_length <= total,
                    "Invalid AppleDouble attribute entry bounds.")
            name = data[position + 11:position + 11 + name_length]
            require(name.endswith(b"\0") and b"\0" not in name[:-1], "Malformed AppleDouble attribute name.")
            try:
                names.add(name[:-1].decode("utf-8"))
            except UnicodeDecodeError as error:
                raise PackagingError("Invalid AppleDouble attribute name encoding.") from error
            position += (11 + name_length + 3) & ~3
    return names


def validate_payload_quarantine(payload):
    """Inspect productbuild's gzip/odc CPIO stream without unpacking an app."""
    metadata_count = 0
    entries = 0
    try:
        with gzip.open(payload, "rb") as stream:
            while True:
                header = stream.read(76)
                require(len(header) == 76 and header[:6] == b"070707", "Malformed or unsupported package CPIO payload.")
                require(re.fullmatch(rb"[0-7]{6}", header[59:65])
                        and re.fullmatch(rb"[0-7]{11}", header[65:76]), "Malformed CPIO numeric field.")
                name_size, file_size = int(header[59:65], 8), int(header[65:76], 8)
                require(0 < name_size <= 4096, "Invalid CPIO path length.")
                raw_name = stream.read(name_size)
                require(len(raw_name) == name_size and raw_name.endswith(b"\0"), "Truncated CPIO path.")
                name = raw_name[:-1].decode("utf-8")
                if name == "TRAILER!!!":
                    require(file_size == 0, "Malformed CPIO trailer.")
                    # Read through gzip EOF to validate its checksum, allowing CPIO block padding.
                    for padding in iter(lambda: stream.read(64 * 1024), b""):
                        require(not any(padding), "Unexpected data after the CPIO trailer.")
                    break
                entries += 1
                if PurePosixPath(name).name.startswith("._"):
                    require(file_size <= 16 * 1024 * 1024, "AppleDouble payload metadata exceeds the inspection limit.")
                    data = stream.read(file_size)
                    require(len(data) == file_size, "Truncated AppleDouble payload metadata.")
                    attributes = appledouble_attribute_names(data)
                    require(QUARANTINE_ATTRIBUTE not in attributes, f"The package contains payload quarantine metadata at {name}.")
                    metadata_count += 1
                else:
                    remaining = file_size
                    while remaining:
                        chunk_size = min(remaining, 64 * 1024)
                        chunk = stream.read(chunk_size)
                        require(len(chunk) == chunk_size, "Truncated CPIO file data.")
                        remaining -= chunk_size
    except (EOFError, gzip.BadGzipFile) as error:
        raise PackagingError("Malformed compressed package payload.") from error
    return {"payload_entries": entries, "appledouble_count": metadata_count, "quarantine_absent": True}


def identity_team(identity, prefix):
    require(identity.startswith(prefix), "The signing identity is not for Mac App Store distribution.")
    match = re.search(r"\(([A-Z0-9]{10})\)$", identity)
    require(match is not None, "The signing identity has no valid Team ID.")
    return match.group(1)


def certificate_metadata(certificate, *, env, der=False):
    form = ["-inform", "DER"] if der else []
    subject = run(["/usr/bin/openssl", "x509", *form, "-noout", "-subject",
                   "-nameopt", "sep_multiline,sname"], env=env, input=certificate).stdout.decode()
    details = run(["/usr/bin/openssl", "x509", *form, "-noout", "-text", "-enddate"],
                  env=env, input=certificate).stdout.decode()
    run(["/usr/bin/openssl", "x509", *form, "-noout", "-checkend", "0"],
        env=env, input=certificate)
    fields = dict(re.findall(r"^\s+(CN|OU)=(.+)$", subject, re.MULTILINE))
    require("CN" in fields and "OU" in fields, "The signing certificate has no subject CN or OU.")
    binary = certificate if der else ssl.PEM_cert_to_DER_cert(certificate.decode())
    enddate = re.search(r"^notAfter=(.+)$", details, re.MULTILINE)
    return {"common_name": fields["CN"], "team_id": fields["OU"],
            "sha1": hashlib.sha1(binary).hexdigest().upper(),
            "sha256": hashlib.sha256(binary).hexdigest(),
            "not_after": enddate.group(1) if enddate else None,
            "details": details}


def validate_certificate(metadata, identity, team, *, installer):
    require(metadata["common_name"] == identity, "The certificate common name differs from the signing identity.")
    require(metadata["team_id"] == team, "The certificate Team ID differs from the application team.")
    marker = INSTALLER_MARKER if installer else APPLICATION_MARKER
    # Apple Security's MacDistributionInstaller policy uses the .6.1.8 marker.
    require(re.search(r"(?<![\d.])" + re.escape(marker) + r"(?![\d.])", metadata["details"]),
            "The certificate has no Mac App Store submission marker.")
    if installer:
        require(INSTALLER_EKU in metadata["details"], "The certificate has no Mac App Store installer extended key usage.")


def validate_installer_identity(identity, team, *, env):
    require(identity_team(identity, INSTALLER_PREFIX) == team, "Installer and application Team IDs differ.")
    listing = run(["/usr/bin/security", "find-identity", "-v"], env=env).stdout.decode()
    fingerprints = {fingerprint for fingerprint, name in
                    re.findall(r'\d+\)\s+([A-Fa-f0-9]{40})\s+"([^"]+)"', listing)
                    if name == identity}
    require(fingerprints, "No valid Mac App Store installer signing identity and private key were found in the keychain.")
    certificates = run(["/usr/bin/security", "find-certificate", "-a", "-c", identity, "-p"], env=env).stdout
    selected = []
    for pem in re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", certificates, re.DOTALL):
        metadata = certificate_metadata(pem, env=env)
        if metadata["sha1"] in {value.upper() for value in fingerprints}:
            validate_certificate(metadata, identity, team, installer=True)
            selected.append(metadata)
    require(len(selected) == 1, "The installer identity must resolve to exactly one valid Mac App Store certificate.")
    return selected[0]


def validate_bundle_info(app, extension):
    for info, identifier, executable in ((app, APP_IDENTIFIER, "Alright"),
                                          (extension, EXTENSION_IDENTIFIER, "AlrightFinderSync")):
        require(info.get("CFBundleIdentifier") == identifier, "Unexpected bundle identifier.")
        require(info.get("CFBundleExecutable") == executable, "Unexpected bundle executable.")
        for key in ("CFBundleShortVersionString", "CFBundleVersion"):
            require(isinstance(info.get(key), str) and re.fullmatch(r"\d+(?:\.\d+){0,2}", info[key]),
                    f"{key} must contain one to three numeric components.")
    require(app.get("CFBundlePackageType") == "APPL", "The main bundle is not an application.")
    require(app.get("LSApplicationCategoryType") == "public.app-category.utilities",
            "The application must declare the Utilities App Store category.")
    require(extension.get("NSExtension", {}).get("NSExtensionPointIdentifier") == "com.apple.FinderSync",
            "The extension is not a Finder Sync extension.")
    require(extension.get("LSUIElement") is True, "The Finder Sync extension must declare LSUIElement=true.")
    for key in ("CFBundleShortVersionString", "CFBundleVersion"):
        require(app[key] == extension[key], f"Application and extension {key} values differ.")


def validate_entitlements(app, extension, team):
    for entitlements in (app, extension):
        require(entitlements.get("com.apple.security.app-sandbox") is True, "Both bundles must enable App Sandbox.")
        for key in ("com.apple.security.get-task-allow", "get-task-allow"):
            require(entitlements.get(key, False) is False, "Distribution signatures must not permit get-task-allow.")
        groups = entitlements.get("com.apple.security.application-groups")
        require(isinstance(groups, list) and groups and all(isinstance(group, str) for group in groups),
                "Both bundles must declare application groups.")
        require(groups == [team + ".com.iisacc.Alright"], "The application group does not match the Alright team.")
    require(app["com.apple.security.application-groups"] == extension["com.apple.security.application-groups"],
            "Application and extension application groups differ.")


def validate_signature_details(details, identifier):
    authorities = re.findall(r"^Authority=(.+)$", details, re.MULTILINE)
    require(authorities and authorities[0].startswith(APPLICATION_PREFIXES),
            "Both bundles must be signed with Apple Distribution or Mac App Distribution.")
    identity = authorities[0]
    prefix = next(prefix for prefix in APPLICATION_PREFIXES if identity.startswith(prefix))
    team = identity_team(identity, prefix)
    require(re.search(r"^TeamIdentifier=" + re.escape(team) + r"$", details, re.MULTILINE),
            "The signature TeamIdentifier differs from the distribution identity.")
    require(re.search(r"^Identifier=" + re.escape(identifier) + r"$", details, re.MULTILINE),
            "The signed identifier differs from Info.plist.")
    require(any(name.startswith("Apple Worldwide Developer Relations") for name in authorities[1:])
            and "Apple Root CA" in authorities[1:], "The distribution signature does not have an Apple WWDR certificate chain.")
    return identity, team


def validate_bundle_signature(bundle, identifier, scratch, *, env):
    run(["/usr/bin/codesign", "--verify", "--strict", str(bundle)], env=env)
    result = run(["/usr/bin/codesign", "-d", "--verbose=4", str(bundle)], env=env)
    identity, team = validate_signature_details((result.stdout + result.stderr).decode(), identifier)
    raw = run(["/usr/bin/codesign", "-d", "--entitlements", ":-", str(bundle)], env=env).stdout
    try:
        entitlements = plistlib.loads(raw)
    except (plistlib.InvalidFileException, ValueError) as error:
        raise PackagingError("The signed entitlements are not a valid property list.") from error
    prefix = scratch / (bundle.name + "-certificate-")
    run(["/usr/bin/codesign", "-d", "--extract-certificates=" + str(prefix), str(bundle)], env=env)
    metadata = certificate_metadata(Path(str(prefix) + "0").read_bytes(), env=env, der=True)
    validate_certificate(metadata, identity, team, installer=False)
    return identity, team, entitlements, metadata


def entitlement_authorized(claimed, allowed):
    if isinstance(claimed, list):
        return isinstance(allowed, list) and all(any(entitlement_authorized(value, option) for option in allowed)
                                                for value in claimed)
    if isinstance(claimed, str) and isinstance(allowed, str) and allowed.endswith("*"):
        return "*" not in allowed[:-1] and claimed.startswith(allowed[:-1])
    return type(claimed) is type(allowed) and claimed == allowed


def validate_provisioning_profile(profile, identifier, team, certificate_sha256, entitlements, *, now=None):
    require(isinstance(profile, dict), "The provisioning profile is not a property list dictionary.")
    require(profile.get("Platform") in (["OSX"], ["macOS"]), "The provisioning profile is not for native macOS.")
    require(profile.get("TeamIdentifier") == [team], "The provisioning profile belongs to a different team.")
    require(profile.get("ApplicationIdentifierPrefix") == [team], "The provisioning profile has an unexpected App ID prefix.")
    try:
        profile_uuid = str(uuid.UUID(profile.get("UUID", "")))
    except (ValueError, AttributeError, TypeError) as error:
        raise PackagingError("The provisioning profile has no valid UUID.") from error
    expiration = profile.get("ExpirationDate")
    require(isinstance(expiration, datetime.datetime), "The provisioning profile has no valid expiration date.")
    expiration = expiration.replace(tzinfo=datetime.timezone.utc) if expiration.tzinfo is None else expiration
    now = now or datetime.datetime.now(datetime.timezone.utc)
    require(expiration > now, "The provisioning profile has expired.")
    creation = profile.get("CreationDate")
    if creation is not None:
        require(isinstance(creation, datetime.datetime), "The provisioning profile has no valid creation date.")
        creation = creation.replace(tzinfo=datetime.timezone.utc) if creation.tzinfo is None else creation
        require(creation <= now, "The provisioning profile is not valid yet.")
    require("ProvisionedDevices" not in profile and profile.get("ProvisionsAllDevices", False) is False,
            "The provisioning profile is not a Mac App Store distribution profile.")
    certificates = profile.get("DeveloperCertificates")
    require(isinstance(certificates, list) and certificates
            and all(isinstance(certificate, bytes) for certificate in certificates),
            "The provisioning profile has no developer certificates.")
    require(certificate_sha256 in {hashlib.sha256(certificate).hexdigest() for certificate in certificates},
            "The provisioning profile does not authorize the actual signing certificate.")
    allowed = profile.get("Entitlements")
    require(isinstance(allowed, dict), "The provisioning profile has no entitlement allowlist.")
    app_id = team + "." + identifier
    require(allowed.get("com.apple.application-identifier") == app_id,
            "The provisioning profile App ID differs from the bundle identifier.")
    require(allowed.get("com.apple.developer.team-identifier") == team,
            "The provisioning profile entitlement Team ID differs from the signing team.")
    for key in ("get-task-allow", "com.apple.security.get-task-allow"):
        require(allowed.get(key, False) is False, "The provisioning profile permits development debugging.")
    require(entitlements.get("com.apple.application-identifier") == app_id
            and entitlements.get("com.apple.developer.team-identifier") == team,
            "Profiled bundles must sign their explicit application and team identifiers.")
    for key, value in entitlements.items():
        # TN3125: sandbox, hardened runtime, and macOS Team-prefixed App Groups
        # are unrestricted and need no profile authorization on macOS.
        if key.startswith("com.apple.security."):
            continue
        require(key in allowed and entitlement_authorized(value, allowed[key]),
                f"The provisioning profile does not authorize signed entitlement {key}.")
    return {"uuid": profile_uuid, "type": "Mac App Store distribution", "team_id": team,
            "application_identifier": app_id, "expiration_date_utc": expiration.isoformat(),
            "signing_certificate_sha256": certificate_sha256,
            "beta_reports_active": allowed.get("beta-reports-active", False) is True}


def validate_embedded_profiles(app, extension, app_signature, extension_signature, *, env):
    paths = [bundle / "Contents/embedded.provisionprofile" for bundle in (app, extension)]
    present = [path.is_file() for path in paths]
    require(present[0] == present[1], "Embed either both host and extension provisioning profiles or neither.")
    if not present[0]:
        return None
    result = {}
    for role, path, identifier, signature in zip(("host", "extension"), paths,
                                                (APP_IDENTIFIER, EXTENSION_IDENTIFIER),
                                                (app_signature, extension_signature)):
        raw = run(["/usr/bin/security", "cms", "-D", "-i", str(path)], env=env).stdout
        try:
            profile = plistlib.loads(raw)
        except (plistlib.InvalidFileException, ValueError) as error:
            raise PackagingError("The embedded provisioning profile could not be decoded.") from error
        result[role] = validate_provisioning_profile(profile, identifier, signature[1],
                                                    signature[3]["sha256"], signature[2])
    return result


def validate_package_signature(output, identity, sha256):
    # macOS 27 labels the Mac Installer Distribution submission certificate
    # "(Development)". The actual certificate type is checked against the
    # keychain submission marker/EKU and exact package signer fingerprint.
    require(re.search(r"^\s*Status: signed by a developer certificate issued by Apple"
                      r"(?: for distribution| \(Development\))\s*$", output, re.MULTILINE),
            "The package signature is not trusted for Apple distribution.")
    require("Signed with a trusted timestamp" in output, "The installer package has no trusted timestamp.")
    leaf = re.search(r"^\s+1\. (.+)$", output, re.MULTILINE)
    require(leaf is not None and leaf.group(1).strip() == identity,
            "The package is not signed with the selected Mac App Store installer identity.")
    fingerprint = re.search(r"SHA256 Fingerprint:\s*([A-Fa-f0-9]{2}(?:[\s:]+[A-Fa-f0-9]{2}){31})(?![A-Fa-f0-9])", output)
    require(fingerprint is not None and re.sub(r"[^A-Fa-f0-9]", "", fingerprint.group(1)).lower() == sha256,
            "The package signer certificate differs from the selected keychain certificate.")
    require("Apple Worldwide Developer Relations" in output and "Apple Root CA" in output,
            "The installer package does not have an Apple WWDR certificate chain.")


def validate_payload_files(output):
    paths = []
    for line in output.splitlines():
        if line in (".", "./", ""):
            continue
        name = line[2:] if line.startswith("./") else line
        # productbuild serializes the canonical app directory's extended
        # attributes as this AppleDouble metadata file outside its payload
        # directory. COPYFILE_DISABLE does not disable this behavior.
        if name == "._Alright.app":
            paths.append(name)
            continue
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts and path.parts[0] == "Alright.app",
                "The package payload contains a path outside Alright.app.")
        require(all(not part.endswith(".app") or part == "Alright.app" for part in path.parts),
                "The package payload contains another application.")
        paths.append(str(path))
    required = {"Alright.app/Contents/Info.plist", "Alright.app/Contents/MacOS/Alright",
                "Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/Info.plist",
                "Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/MacOS/AlrightFinderSync"}
    require(required.issubset(paths), "The package payload is missing the application or Finder Sync extension.")
    return paths


def validate_package_info(xml, app_info):
    root = ET.fromstring(xml)
    require(root.tag == "pkg-info" and root.get("install-location") == "/Applications",
            "The component installation destination must be /Applications.")
    require(root.get("identifier") == APP_IDENTIFIER, "Unexpected component package identifier.")
    require(root.find("scripts") is None, "The App Store package must not contain installer scripts.")
    bundles = root.findall("bundle")
    require(len(bundles) == 1 and bundles[0].get("id") == APP_IDENTIFIER,
            "The component package must contain exactly the Alright application bundle.")
    bundle = bundles[0]
    require(bundle.get("path") in ("Alright.app", "./Alright.app"),
            "The package metadata has an unexpected bundle destination.")
    for key in ("CFBundleVersion", "CFBundleShortVersionString"):
        require(bundle.get(key) == app_info[key], f"The package {key} differs from the signed bundle.")
    require(root.get("version") == app_info["CFBundleShortVersionString"],
            "The component package version differs from the signed application.")
    return {"identifier": root.get("identifier"), "version": root.get("version"),
            "install_location": root.get("install-location"), "application_destination": "/Applications/Alright.app"}


def validate_distribution(xml, app_info):
    root = ET.fromstring(xml)
    product = root.find("product")
    require(root.tag == "installer-gui-script" and product is not None
            and product.get("id") == APP_IDENTIFIER
            and product.get("version") == app_info["CFBundleShortVersionString"],
            "Unexpected product archive identifier or version.")
    choices = root.findall("choice")
    destinations = [choice.get("customLocation") for choice in choices if choice.get("customLocation")]
    require(destinations == ["/Applications"], "The product archive must install only to /Applications.")
    packages = [reference for reference in root.findall("pkg-ref") if reference.text and reference.text.strip()]
    require(len(packages) == 1 and packages[0].get("id") == APP_IDENTIFIER,
            "The product archive must reference exactly one Alright component package.")


def public_certificate(metadata):
    return {key: metadata[key] for key in ("common_name", "team_id", "sha256", "not_after")}


def package(build, installer_identity):
    repo = Path(__file__).resolve().parents[1]
    build = build.resolve()
    require(build == repo / "build", "Use the repository's canonical build/ directory.")
    app = build / "bin/Alright.app"
    extension = app / "Contents/PlugIns/AlrightFinderSync.appex"
    require(app.is_dir() and extension.is_dir(), "Build AlrightBundle before packaging.")
    require(list(build.rglob("*.app")) == [app], "build/ must contain exactly the canonical Alright.app.")
    app_info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    extension_info = plistlib.loads((extension / "Contents/Info.plist").read_bytes())
    validate_bundle_info(app_info, extension_info)
    packaging = build / "packaging"
    packaging.mkdir(exist_ok=True)
    destination = build / "appstore"
    destination.mkdir(exist_ok=True)
    filename = f"Alright-{app_info['CFBundleShortVersionString']}-{app_info['CFBundleVersion']}-macOS-AppStore.pkg"
    final = destination / filename
    with tempfile.TemporaryDirectory(prefix="appstore-", dir=packaging) as temporary:
        scratch = Path(temporary)
        env = dict(os.environ, TMPDIR=str(scratch), LC_ALL="C", LANG="C")
        quarantine = sanitize_bundle_quarantine(app, env=env)
        app_signature = validate_bundle_signature(app, APP_IDENTIFIER, scratch, env=env)
        extension_signature = validate_bundle_signature(extension, EXTENSION_IDENTIFIER, scratch, env=env)
        identity, team, entitlements, app_certificate = app_signature
        extension_identity, extension_team, extension_entitlements, extension_certificate = extension_signature
        require(identity == extension_identity and team == extension_team
                and app_certificate["sha256"] == extension_certificate["sha256"],
                "Application and extension must use the same distribution certificate and Team ID.")
        validate_entitlements(entitlements, extension_entitlements, team)
        profiles = validate_embedded_profiles(app, extension, app_signature, extension_signature, env=env)
        installer_certificate = validate_installer_identity(installer_identity, team, env=env)
        candidate = scratch / filename
        run(["/usr/bin/productbuild", "--component", str(app), "/Applications", "--sign",
             installer_identity, "--timestamp", str(candidate)], env=env)
        signature = run(["/usr/sbin/pkgutil", "--check-signature", str(candidate)], env=env).stdout.decode()
        validate_package_signature(signature, installer_identity, installer_certificate["sha256"])
        payload_output = run(["/usr/sbin/pkgutil", "--payload-files", str(candidate)], env=env).stdout.decode()
        paths = validate_payload_files(payload_output)
        if profiles:
            require({"Alright.app/Contents/embedded.provisionprofile",
                     "Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/embedded.provisionprofile"}.issubset(paths),
                    "The package payload is missing an embedded provisioning profile.")
        expanded = scratch / "metadata"
        # --expand preserves compressed Payloads. --expand-full would create an app copy.
        run(["/usr/sbin/pkgutil", "--expand", str(candidate), str(expanded)], env=env)
        require(not list(expanded.rglob("*.app")), "Package validation must not unpack application bundles.")
        components = list(expanded.rglob("PackageInfo"))
        require(len(components) == 1 and (expanded / "Distribution").is_file(),
                "The product archive must contain exactly one component package and a Distribution file.")
        component = validate_package_info(components[0].read_text(), app_info)
        validate_distribution((expanded / "Distribution").read_text(), app_info)
        payloads = list(expanded.rglob("Payload"))
        require(len(payloads) == 1, "The product archive must contain exactly one payload.")
        payload_quarantine = validate_payload_quarantine(payloads[0])
        hasher = hashlib.sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        require(list(build.rglob("*.app")) == [app], "Packaging created another application bundle.")
        report = {"schema_version": 1, "package": filename, "sha256": digest,
                  "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "source_app": "build/bin/Alright.app", "bundle_identifier": APP_IDENTIFIER,
                  "version": app_info["CFBundleShortVersionString"], "build_number": app_info["CFBundleVersion"],
                  "team_id": team, "application_certificate": public_certificate(app_certificate),
                  "installer_certificate": public_certificate(installer_certificate),
                  "sandbox_enabled": True, "get_task_allow": False,
                  "application_groups": entitlements["com.apple.security.application-groups"],
                  "provisioning_profiles": profiles,
                  "testflight_provisioning": "locally_verified" if profiles else "not_present",
                  "quarantine_sanitization": quarantine,
                  "payload_quarantine_validation": payload_quarantine,
                  "component": component, "payload_file_count": len(paths),
                  "local_signature_validation": "passed", "trusted_installer_timestamp": True,
                  "app_store_connect_validation": "not_performed", "app_store_connect_upload": "not_performed",
                  "installation_test": "not_performed"}
        candidate.replace(final)
        final.with_suffix(".sha256").write_text(f"{digest}  {filename}\n")
        final.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--installer-identity", required=True)
    args = parser.parse_args()
    try:
        result = package(args.build, args.installer_identity)
    except (PackagingError, OSError, ValueError, plistlib.InvalidFileException, ET.ParseError) as error:
        print(f"App Store packaging failed: {error}", file=sys.stderr)
        return 1
    print(f"Locally verified App Store package: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
