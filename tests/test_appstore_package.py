"""Exercise App Store package rejection paths without copying or signing an app."""
from pathlib import Path
from unittest import mock
import importlib.util
import datetime
import hashlib
import gzip
import io
import struct
import plistlib
import subprocess
import sys
import unittest


SPEC = importlib.util.spec_from_file_location("appstore_package", Path(__file__).resolve().parents[1] / "tools/PackageAppStore.py")
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)
TEAM = "TESTTEAM01"
APPLICATION = f"Apple Distribution: Example Test ({TEAM})"
INSTALLER = f"3rd Party Mac Developer Installer: Example Test ({TEAM})"
SHA1 = "AB" * 20
SHA256 = "cd" * 32
APP_INFO = {"CFBundleIdentifier": PACKAGE.APP_IDENTIFIER, "CFBundleExecutable": "Alright",
            "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "0.6.1", "CFBundleVersion": "7",
            "LSApplicationCategoryType": "public.app-category.utilities"}
EXTENSION_INFO = {"CFBundleIdentifier": PACKAGE.EXTENSION_IDENTIFIER, "CFBundleExecutable": "AlrightFinderSync",
                  "CFBundleShortVersionString": "0.6.1", "CFBundleVersion": "7",
                  "LSUIElement": True,
                  "NSExtension": {"NSExtensionPointIdentifier": "com.apple.FinderSync"}}
ENTITLEMENTS = {"com.apple.security.app-sandbox": True,
                "com.apple.security.application-groups": [TEAM + ".com.iisacc.Alright"]}
PROFILE_CERTIFICATE = b"TEST PROFILE CERTIFICATE DER"
PROFILE_CERTIFICATE_SHA256 = hashlib.sha256(PROFILE_CERTIFICATE).hexdigest()
PROFILE = {"UUID": "b83e8eca-61af-4200-be48-d1e61d3fb3d1", "Platform": ["OSX"],
           "TeamIdentifier": [TEAM], "ApplicationIdentifierPrefix": [TEAM],
           "ExpirationDate": datetime.datetime(2099, 1, 1), "DeveloperCertificates": [PROFILE_CERTIFICATE],
           "Entitlements": {"com.apple.application-identifier": TEAM + "." + PACKAGE.APP_IDENTIFIER,
                            "com.apple.developer.team-identifier": TEAM,
                            "keychain-access-groups": [TEAM + ".*"]}}
PROFILED_ENTITLEMENTS = dict(ENTITLEMENTS, **{"com.apple.application-identifier": TEAM + "." + PACKAGE.APP_IDENTIFIER,
                                             "com.apple.developer.team-identifier": TEAM})
INSTALLER_CERTIFICATE = {"common_name": INSTALLER, "team_id": TEAM, "sha1": SHA1, "sha256": SHA256,
                         "not_after": "Jan 1 00:00:00 2099 GMT",
                         "details": f"{PACKAGE.INSTALLER_MARKER}: critical\n{PACKAGE.INSTALLER_EKU}"}
COMPONENT_XML = f'''<pkg-info identifier="{PACKAGE.APP_IDENTIFIER}" version="0.6.1" install-location="/Applications">
    <bundle path="./Alright.app" id="{PACKAGE.APP_IDENTIFIER}" CFBundleShortVersionString="0.6.1" CFBundleVersion="7"/>
    <bundle-version><bundle id="{PACKAGE.APP_IDENTIFIER}"/></bundle-version>
</pkg-info>'''
DISTRIBUTION_XML = f'''<installer-gui-script minSpecVersion="2">
    <product id="{PACKAGE.APP_IDENTIFIER}" version="0.6.1"/>
    <choice id="default"/><choice id="{PACKAGE.APP_IDENTIFIER}" customLocation="/Applications"/>
    <pkg-ref id="{PACKAGE.APP_IDENTIFIER}" version="0.6.1">#{PACKAGE.APP_IDENTIFIER}.pkg</pkg-ref>
</installer-gui-script>'''
PAYLOAD = "\n".join((".", "./Alright.app", "./Alright.app/Contents/Info.plist",
                     "./Alright.app/Contents/MacOS/Alright",
                     "./Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/Info.plist",
                     "./Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/MacOS/AlrightFinderSync"))


def signature_details(identity=APPLICATION, team=TEAM):
    return (f"Identifier={PACKAGE.APP_IDENTIFIER}\nAuthority={identity}\n"
            "Authority=Apple Worldwide Developer Relations Certification Authority\n"
            f"Authority=Apple Root CA\nTeamIdentifier={team}\n")


def package_signature(identity=INSTALLER):
    fingerprint = " ".join(SHA256[index:index + 2].upper() for index in range(0, 64, 2))
    return ("Package \"Alright.pkg\":\n"
            "  Status: signed by a developer certificate issued by Apple for distribution\n"
            "  Signed with a trusted timestamp on: 2098-01-01 00:00:00 +0000\n"
            f"  Certificate Chain:\n   1. {identity}\n"
            f"      SHA256 Fingerprint:\n          {fingerprint}\n"
            "   2. Apple Worldwide Developer Relations Certification Authority\n"
            "   3. Apple Root CA\n")


class AppStorePackageTests(unittest.TestCase):
    def test_distribution_metadata_matches(self):
        PACKAGE.validate_bundle_info(APP_INFO, EXTENSION_INFO)
        PACKAGE.validate_entitlements(ENTITLEMENTS, ENTITLEMENTS, TEAM)
        self.assertEqual(PACKAGE.validate_signature_details(signature_details(), PACKAGE.APP_IDENTIFIER),
                         (APPLICATION, TEAM))

    def test_extension_build_mismatch_is_rejected(self):
        extension = dict(EXTENSION_INFO, CFBundleVersion="8")
        with self.assertRaisesRegex(PACKAGE.PackagingError, "CFBundleVersion values differ"):
            PACKAGE.validate_bundle_info(APP_INFO, extension)

    def test_finder_sync_extension_requires_ls_ui_element(self):
        for value in (False, None, "true", 1):
            with self.subTest(value=value), self.assertRaisesRegex(PACKAGE.PackagingError, "LSUIElement"):
                PACKAGE.validate_bundle_info(APP_INFO, dict(EXTENSION_INFO, LSUIElement=value))

    def test_invalid_bundle_identifier_is_rejected(self):
        for key, value in (("CFBundleIdentifier", "com.example.Other"),
                           ("CFBundleExecutable", "Other"), ("CFBundlePackageType", "BNDL"),
                           ("LSApplicationCategoryType", "public.app-category.games")):
            with self.subTest(key=key), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_bundle_info(dict(APP_INFO, **{key: value}), EXTENSION_INFO)

    def test_unsafe_or_missing_version_is_rejected(self):
        for value in ("../../Elsewhere", "1.0-beta", "1.2.3.4", None, 7):
            with self.subTest(value=value), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_bundle_info(dict(APP_INFO, CFBundleVersion=value), EXTENSION_INFO)

    def test_sandbox_missing_or_wrong_type_is_rejected(self):
        for value in (False, None, "true", 1):
            with self.subTest(value=value), self.assertRaisesRegex(PACKAGE.PackagingError, "App Sandbox"):
                PACKAGE.validate_entitlements(dict(ENTITLEMENTS, **{"com.apple.security.app-sandbox": value}),
                                              ENTITLEMENTS, TEAM)

    def test_both_get_task_allow_spellings_are_rejected(self):
        for key in ("get-task-allow", "com.apple.security.get-task-allow"):
            with self.subTest(key=key), self.assertRaisesRegex(PACKAGE.PackagingError, "get-task-allow"):
                PACKAGE.validate_entitlements(ENTITLEMENTS, dict(ENTITLEMENTS, **{key: True}), TEAM)

    def test_mismatching_or_missing_app_group_is_rejected(self):
        for groups in ([], ["OTHERTEAM1.com.iisacc.Alright"], ["group.com.example.Alright"], "invalid"):
            with self.subTest(groups=groups), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_entitlements(ENTITLEMENTS,
                                              dict(ENTITLEMENTS, **{"com.apple.security.application-groups": groups}), TEAM)

    def test_developer_id_and_development_app_signatures_are_rejected(self):
        for identity in (f"Developer ID Application: Example Test ({TEAM})", f"Apple Development: Example Test ({TEAM})"):
            with self.subTest(identity=identity), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_signature_details(signature_details(identity), PACKAGE.APP_IDENTIFIER)

    def test_legacy_app_distribution_signature_is_accepted(self):
        identity = f"3rd Party Mac Developer Application: Example Test ({TEAM})"
        self.assertEqual(PACKAGE.validate_signature_details(signature_details(identity), PACKAGE.APP_IDENTIFIER),
                         (identity, TEAM))

    def test_signature_team_mismatch_is_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "TeamIdentifier"):
            PACKAGE.validate_signature_details(signature_details(team="OTHERTEAM1"), PACKAGE.APP_IDENTIFIER)

    def test_signature_identifier_mismatch_is_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "signed identifier"):
            PACKAGE.validate_signature_details(signature_details(), PACKAGE.EXTENSION_IDENTIFIER)

    def test_signature_without_apple_chain_is_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "Apple WWDR"):
            PACKAGE.validate_signature_details(signature_details().replace("Authority=Apple Root CA\n", ""),
                                               PACKAGE.APP_IDENTIFIER)

    def test_bundle_verification_extracts_certificates_with_optional_argument(self):
        bundle = Path("/example/build/bin/Alright.app")
        scratch = Path("/example/build/packaging/validation")
        outputs = [subprocess.CompletedProcess([], 0, b"", b""),
                   subprocess.CompletedProcess([], 0, b"", signature_details().encode()),
                   subprocess.CompletedProcess([], 0, plistlib.dumps(ENTITLEMENTS), b""),
                   subprocess.CompletedProcess([], 0, b"", b"")]
        certificate = dict(INSTALLER_CERTIFICATE, common_name=APPLICATION,
                           details=PACKAGE.APPLICATION_MARKER)
        with mock.patch.object(PACKAGE, "run", side_effect=outputs) as command, \
                mock.patch.object(Path, "read_bytes", return_value=b"TEST DER CERTIFICATE") as read, \
                mock.patch.object(PACKAGE, "certificate_metadata", return_value=certificate) as metadata:
            result = PACKAGE.validate_bundle_signature(bundle, PACKAGE.APP_IDENTIFIER, scratch, env={})
        self.assertEqual(command.call_args_list[0].args[0],
                         ["/usr/bin/codesign", "--verify", "--strict", str(bundle)])
        self.assertEqual(command.call_args_list[-1].args[0],
                         ["/usr/bin/codesign", "-d",
                          "--extract-certificates=/example/build/packaging/validation/Alright.app-certificate-", str(bundle)])
        read.assert_called_once_with()
        metadata.assert_called_once_with(b"TEST DER CERTIFICATE", env={}, der=True)
        self.assertEqual(result, (APPLICATION, TEAM, ENTITLEMENTS, certificate))

    def test_matching_certificate_metadata_is_accepted(self):
        PACKAGE.validate_certificate(INSTALLER_CERTIFICATE, INSTALLER, TEAM, installer=True)

    def test_certificate_subject_team_and_type_mismatches_are_rejected(self):
        for change in ({"common_name": APPLICATION}, {"team_id": "OTHERTEAM1"},
                       {"details": "1.2.840.113635.100.6.1.14"},
                       {"details": PACKAGE.INSTALLER_MARKER},
                       {"details": PACKAGE.INSTALLER_MARKER + "0\n" + PACKAGE.INSTALLER_EKU}):
            with self.subTest(change=change), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_certificate(dict(INSTALLER_CERTIFICATE, **change), INSTALLER, TEAM, installer=True)

    def test_keychain_identity_and_certificate_fingerprint_match(self):
        listing = subprocess.CompletedProcess([], 0, f'  1) {SHA1} "{INSTALLER}"\n'.encode(), b"")
        certificates = subprocess.CompletedProcess([], 0,
                                                    b"-----BEGIN CERTIFICATE-----\nTEST FIXTURE\n-----END CERTIFICATE-----", b"")
        with mock.patch.object(PACKAGE, "run", side_effect=[listing, certificates]) as command, \
                mock.patch.object(PACKAGE, "certificate_metadata", return_value=INSTALLER_CERTIFICATE):
            result = PACKAGE.validate_installer_identity(INSTALLER, TEAM, env={})
        self.assertEqual(result["sha256"], SHA256)
        self.assertEqual(command.call_args_list[0].args[0], ["/usr/bin/security", "find-identity", "-v"])

    def test_valid_keychain_identity_is_required(self):
        listing = subprocess.CompletedProcess([], 0, b"0 valid identities found\n", b"")
        with mock.patch.object(PACKAGE, "run", return_value=listing), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "No valid Mac App Store installer"):
            PACKAGE.validate_installer_identity(INSTALLER, TEAM, env={})

    def test_keychain_certificate_fingerprint_mismatch_is_rejected(self):
        listing = subprocess.CompletedProcess([], 0, f'  1) {SHA1} "{INSTALLER}"\n'.encode(), b"")
        certificates = subprocess.CompletedProcess([], 0,
                                                    b"-----BEGIN CERTIFICATE-----\nTEST FIXTURE\n-----END CERTIFICATE-----", b"")
        different = dict(INSTALLER_CERTIFICATE, sha1="12" * 20)
        with mock.patch.object(PACKAGE, "run", side_effect=[listing, certificates]), \
                mock.patch.object(PACKAGE, "certificate_metadata", return_value=different), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "exactly one"):
            PACKAGE.validate_installer_identity(INSTALLER, TEAM, env={})

    def test_wrong_installer_identity_is_rejected_before_keychain_access(self):
        for identity in (f"Developer ID Installer: Example Test ({TEAM})",
                         "3rd Party Mac Developer Installer: Example Test (OTHERTEAM1)"):
            with self.subTest(identity=identity), mock.patch.object(PACKAGE, "run") as command, \
                    self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_installer_identity(identity, TEAM, env={})
            command.assert_not_called()

    def test_package_signature_matches_certificate_fingerprint(self):
        PACKAGE.validate_package_signature(package_signature(), INSTALLER, SHA256)

    def test_macos27_submission_certificate_status_is_accepted(self):
        output = package_signature().replace("issued by Apple for distribution", "issued by Apple (Development)")
        PACKAGE.validate_package_signature(output, INSTALLER, SHA256)
        wrong_leaf = output.replace(INSTALLER, f"Apple Development: Example Test ({TEAM})")
        with self.assertRaisesRegex(PACKAGE.PackagingError, "selected Mac App Store installer"):
            PACKAGE.validate_package_signature(wrong_leaf, INSTALLER, SHA256)

    def test_package_signature_wrong_identity_or_fingerprint_is_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "selected Mac App Store installer"):
            PACKAGE.validate_package_signature(package_signature("Developer ID Installer: Example Test"), INSTALLER, SHA256)
        with self.assertRaisesRegex(PACKAGE.PackagingError, "selected keychain certificate"):
            PACKAGE.validate_package_signature(package_signature(), INSTALLER, "ef" * 32)

    def test_package_timestamp_and_trust_are_required(self):
        for original, replacement in (("Signed with a trusted timestamp", "No timestamp"),
                                      ("signed by a developer certificate issued by Apple for distribution", "unsigned")):
            with self.subTest(original=original), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_package_signature(package_signature().replace(original, replacement), INSTALLER, SHA256)

    def test_payload_contains_application_and_extension(self):
        self.assertEqual(len(PACKAGE.validate_payload_files(PAYLOAD)), 5)

    def test_payload_accepts_only_exact_root_appledouble_app_metadata(self):
        paths = PACKAGE.validate_payload_files(PAYLOAD + "\n./._Alright.app")
        self.assertEqual(paths[-1], "._Alright.app")

    def test_payload_rejects_escaping_paths_and_other_apps(self):
        for extra in ("../Other.app", "/Applications/Alright.app", "./Other.app/Contents/Info.plist",
                      "./Alright.app/Contents/Helper.app/Contents/Info.plist", "./Alright.app/../Outside",
                      "./._Other.app", "./._Alright.app.evil", "./OtherRootFile", "./._Alright.app/Child"):
            with self.subTest(extra=extra), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_payload_files(PAYLOAD + "\n" + extra)

    def test_payload_missing_extension_is_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "missing"):
            PACKAGE.validate_payload_files("\n".join(PAYLOAD.splitlines()[:4]))

    def test_package_metadata_matches_app(self):
        component = PACKAGE.validate_package_info(COMPONENT_XML, APP_INFO)
        self.assertEqual(component["application_destination"], "/Applications/Alright.app")
        PACKAGE.validate_distribution(DISTRIBUTION_XML, APP_INFO)

    def test_package_metadata_mismatches_are_rejected(self):
        for original, replacement in (("/Applications", "/tmp"), ("CFBundleVersion=\"7\"", "CFBundleVersion=\"8\""),
                                      ("./Alright.app", "./Other.app"), ("version=\"0.6.1\"", "version=\"0.6.2\"")):
            with self.subTest(original=original), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_package_info(COMPONENT_XML.replace(original, replacement), APP_INFO)

    def test_installer_scripts_are_rejected(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "installer scripts"):
            PACKAGE.validate_package_info(COMPONENT_XML.replace("</pkg-info>", "<scripts/></pkg-info>"), APP_INFO)

    def test_distribution_destination_and_version_mismatches_are_rejected(self):
        for original, replacement in (("/Applications", "/Library"), ("version=\"0.6.1\"", "version=\"1.0\"")):
            with self.subTest(original=original), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_distribution(DISTRIBUTION_XML.replace(original, replacement), APP_INFO)

    def test_tool_failures_do_not_echo_captured_sensitive_output(self):
        result = subprocess.CompletedProcess([], 1, b"private fixture output", b"secret fixture stderr")
        with mock.patch.object(PACKAGE.subprocess, "run", return_value=result), \
                self.assertRaises(PACKAGE.PackagingError) as caught:
            PACKAGE.run(["/usr/bin/security", "find-identity", "-v"], env={})
        self.assertNotIn("private fixture", str(caught.exception))
        self.assertNotIn("secret fixture", str(caught.exception))

    def test_distribution_profile_matches_bundle_and_certificate(self):
        result = PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM,
                                                       PROFILE_CERTIFICATE_SHA256, PROFILED_ENTITLEMENTS)
        self.assertEqual(result["type"], "Mac App Store distribution")
        self.assertEqual(result["uuid"], PROFILE["UUID"])
        self.assertNotIn("DeveloperCertificates", result)
        self.assertNotIn("Entitlements", result)

    def test_profile_platform_team_prefix_and_expiration_failures(self):
        for change in ({"Platform": ["iOS"]}, {"TeamIdentifier": ["OTHERTEAM1"]},
                       {"ApplicationIdentifierPrefix": ["OTHERTEAM1"]}, {"UUID": "invalid"},
                       {"ExpirationDate": datetime.datetime(2000, 1, 1)},
                       {"ExpirationDate": "2099-01-01"}, {"CreationDate": datetime.datetime(2098, 1, 1)}):
            with self.subTest(change=change), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_provisioning_profile(dict(PROFILE, **change), PACKAGE.APP_IDENTIFIER, TEAM,
                                                       PROFILE_CERTIFICATE_SHA256, PROFILED_ENTITLEMENTS)

    def test_development_device_and_developer_id_profiles_are_rejected(self):
        for change in ({"ProvisionedDevices": []}, {"ProvisionedDevices": ["TEST DEVICE"]},
                       {"ProvisionsAllDevices": True}, {"ProvisionsAllDevices": "false"}):
            with self.subTest(change=change), self.assertRaisesRegex(PACKAGE.PackagingError, "Mac App Store distribution"):
                PACKAGE.validate_provisioning_profile(dict(PROFILE, **change), PACKAGE.APP_IDENTIFIER, TEAM,
                                                       PROFILE_CERTIFICATE_SHA256, PROFILED_ENTITLEMENTS)

    def test_profile_must_include_actual_signing_certificate(self):
        for certificates in ([], [b"OTHER CERTIFICATE"], ["INVALID CERTIFICATE DATA"]):
            with self.subTest(certificates=certificates), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_provisioning_profile(dict(PROFILE, DeveloperCertificates=certificates),
                                                       PACKAGE.APP_IDENTIFIER, TEAM, PROFILE_CERTIFICATE_SHA256,
                                                       PROFILED_ENTITLEMENTS)

    def test_profile_application_team_and_debug_entitlements_failures(self):
        for change in ({"com.apple.application-identifier": TEAM + ".com.example.Other"},
                       {"com.apple.developer.team-identifier": "OTHERTEAM1"},
                       {"get-task-allow": True}, {"com.apple.security.get-task-allow": True}):
            profile = dict(PROFILE, Entitlements=dict(PROFILE["Entitlements"], **change))
            with self.subTest(change=change), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_provisioning_profile(profile, PACKAGE.APP_IDENTIFIER, TEAM,
                                                       PROFILE_CERTIFICATE_SHA256, PROFILED_ENTITLEMENTS)

    def test_profile_requires_signed_explicit_application_identity(self):
        with self.assertRaisesRegex(PACKAGE.PackagingError, "explicit application and team"):
            PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM,
                                                   PROFILE_CERTIFICATE_SHA256, ENTITLEMENTS)

    def test_profile_authorizes_restricted_entitlements_with_prefix_wildcards(self):
        signed = dict(PROFILED_ENTITLEMENTS, **{"keychain-access-groups": [TEAM + ".com.iisacc.Alright"]})
        PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM, PROFILE_CERTIFICATE_SHA256, signed)
        signed["keychain-access-groups"].append("OTHERTEAM1.com.example.Other")
        with self.assertRaisesRegex(PACKAGE.PackagingError, "does not authorize signed entitlement"):
            PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM, PROFILE_CERTIFICATE_SHA256, signed)
        with self.assertRaisesRegex(PACKAGE.PackagingError, "does not authorize signed entitlement"):
            PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM, PROFILE_CERTIFICATE_SHA256,
                                                   dict(PROFILED_ENTITLEMENTS, **{"com.apple.developer.icloud-services": ["CloudKit"]}))

    def test_unrestricted_macos_entitlements_need_no_profile_allowlist(self):
        self.assertNotIn("com.apple.security.application-groups", PROFILE["Entitlements"])
        PACKAGE.validate_provisioning_profile(PROFILE, PACKAGE.APP_IDENTIFIER, TEAM,
                                               PROFILE_CERTIFICATE_SHA256, PROFILED_ENTITLEMENTS)

    def test_optional_embedded_profiles_preserve_profileless_store_packaging(self):
        with mock.patch.object(Path, "is_file", side_effect=[False, False]), \
                mock.patch.object(PACKAGE, "run") as command:
            result = PACKAGE.validate_embedded_profiles(Path("/example/Alright.app"), Path("/example/extension"),
                                                       (), (), env={})
        self.assertIsNone(result)
        command.assert_not_called()

    def test_both_embedded_profiles_are_required_when_one_is_present(self):
        with mock.patch.object(Path, "is_file", side_effect=[True, False]), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "both host and extension"):
            PACKAGE.validate_embedded_profiles(Path("/example/Alright.app"), Path("/example/extension"), (), (), env={})


class QuarantineSanitizationTests(unittest.TestCase):
    APP = Path("/example/build/bin/Alright.app")
    PROFILE = APP / "Contents/embedded.provisionprofile"
    WALK = [(str(APP), ["Contents", "ExternalDirectoryLink"], []),
            (str(APP / "Contents"), [], ["embedded.provisionprofile", "ExternalFileLink"])]

    @staticmethod
    def output(attributes=()):
        return subprocess.CompletedProcess([], 0, "\n".join(attributes).encode(), b"")

    def test_only_quarantine_is_removed_from_every_bundle_entry_without_following_links(self):
        deleted = set()

        def xattr(command, *, env):
            self.assertEqual(command[0], "/usr/bin/xattr")
            path = Path(command[-1])
            if command[1] == "-d":
                self.assertEqual(command[1:-1], ["-d", "-s", "com.apple.quarantine"])
                deleted.add(path)
                return self.output()
            self.assertEqual(command[1:-1], ["-s"])
            attributes = ["com.apple.FinderInfo", "com.apple.metadata:custom"]
            if path in (self.APP, self.APP / "Contents", self.PROFILE) and path not in deleted:
                attributes.append("com.apple.quarantine")
            return self.output(attributes)

        with mock.patch.object(PACKAGE.os, "walk", return_value=self.WALK) as walk, \
                mock.patch.object(PACKAGE, "run", side_effect=xattr) as command:
            result = PACKAGE.sanitize_bundle_quarantine(self.APP, env={})
        self.assertEqual(deleted, {self.APP, self.APP / "Contents", self.PROFILE})
        self.assertEqual(result["removed_count"], 3)
        self.assertEqual(result["inspected_count"], 5)
        self.assertTrue(result["verified_absent"])
        self.assertFalse(walk.call_args.kwargs["followlinks"])
        listed = [Path(call.args[0][-1]) for call in command.call_args_list if call.args[0][1] == "-s"]
        self.assertEqual(set(listed), {self.APP, self.APP / "Contents", self.PROFILE,
                                      self.APP / "ExternalDirectoryLink", self.APP / "Contents/ExternalFileLink"})

    def test_already_clean_bundle_preserves_other_attributes_without_mutation(self):
        with mock.patch.object(PACKAGE.os, "walk", return_value=self.WALK), \
                mock.patch.object(PACKAGE, "run", return_value=self.output(["com.apple.FinderInfo"])) as command:
            result = PACKAGE.sanitize_bundle_quarantine(self.APP, env={})
        self.assertEqual(result["removed_count"], 0)
        self.assertTrue(all(call.args[0][1] == "-s" for call in command.call_args_list))

    def test_quarantine_remaining_after_successful_delete_is_rejected(self):
        outputs = [self.output(["com.apple.quarantine"]), self.output(), self.output(["com.apple.quarantine"])]
        with mock.patch.object(PACKAGE.os, "walk", return_value=[(str(self.APP), [], [])]), \
                mock.patch.object(PACKAGE, "run", side_effect=outputs), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "quarantine.*remains"):
            PACKAGE.sanitize_bundle_quarantine(self.APP, env={})

    def test_loss_of_unrelated_attribute_is_rejected(self):
        outputs = [self.output(["com.apple.quarantine", "com.apple.FinderInfo"]), self.output(), self.output()]
        with mock.patch.object(PACKAGE.os, "walk", return_value=[(str(self.APP), [], [])]), \
                mock.patch.object(PACKAGE, "run", side_effect=outputs), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "unrelated extended attributes"):
            PACKAGE.sanitize_bundle_quarantine(self.APP, env={})

    def test_attribute_listing_and_removal_failures_are_propagated(self):
        for outputs in ([PACKAGE.PackagingError("attribute listing failed")],
                        [self.output(["com.apple.quarantine"]), PACKAGE.PackagingError("attribute removal failed")]):
            with self.subTest(outputs=outputs), \
                    mock.patch.object(PACKAGE.os, "walk", return_value=[(str(self.APP), [], [])]), \
                    mock.patch.object(PACKAGE, "run", side_effect=outputs), \
                    self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.sanitize_bundle_quarantine(self.APP, env={})

    def test_bundle_traversal_errors_are_not_swallowed(self):
        def inaccessible(*args, **kwargs):
            kwargs["onerror"](PermissionError("test inaccessible directory"))
            return iter(())

        with mock.patch.object(PACKAGE.os, "walk", side_effect=inaccessible), \
                self.assertRaises(PermissionError):
            PACKAGE.sanitize_bundle_quarantine(self.APP, env={})

    def test_symlinked_app_root_is_rejected(self):
        with mock.patch.object(Path, "is_symlink", return_value=True), \
                mock.patch.object(PACKAGE, "run") as command, \
                self.assertRaisesRegex(PACKAGE.PackagingError, "symbolic link"):
            PACKAGE.sanitize_bundle_quarantine(self.APP, env={})
        command.assert_not_called()


class EmbeddedProfileDecodeTests(unittest.TestCase):
    def test_embedded_profiles_are_cms_decoded_and_match_each_bundle(self):
        extension_entitlements = dict(PROFILED_ENTITLEMENTS,
                                      **{"com.apple.application-identifier": TEAM + "." + PACKAGE.EXTENSION_IDENTIFIER})
        extension_profile = dict(PROFILE, Entitlements=dict(PROFILE["Entitlements"],
                                                          **{"com.apple.application-identifier": TEAM + "." + PACKAGE.EXTENSION_IDENTIFIER}))
        outputs = [subprocess.CompletedProcess([], 0, plistlib.dumps(profile), b"") for profile in (PROFILE, extension_profile)]
        certificate = {"sha256": PROFILE_CERTIFICATE_SHA256}
        app_signature = (APPLICATION, TEAM, PROFILED_ENTITLEMENTS, certificate)
        extension_signature = (APPLICATION, TEAM, extension_entitlements, certificate)
        with mock.patch.object(Path, "is_file", side_effect=[True, True]), \
                mock.patch.object(PACKAGE, "run", side_effect=outputs) as command:
            result = PACKAGE.validate_embedded_profiles(Path("/example/Alright.app"), Path("/example/extension"),
                                                       app_signature, extension_signature, env={})
        self.assertEqual(command.call_args_list[0].args[0],
                         ["/usr/bin/security", "cms", "-D", "-i", "/example/Alright.app/Contents/embedded.provisionprofile"])
        self.assertEqual(result["extension"]["application_identifier"], TEAM + "." + PACKAGE.EXTENSION_IDENTIFIER)

    def test_invalid_embedded_cms_property_list_is_rejected(self):
        output = subprocess.CompletedProcess([], 0, b"NOT A PROPERTY LIST", b"")
        with mock.patch.object(Path, "is_file", side_effect=[True, True]), \
                mock.patch.object(PACKAGE, "run", return_value=output), \
                self.assertRaisesRegex(PACKAGE.PackagingError, "could not be decoded"):
            PACKAGE.validate_embedded_profiles(Path("/example/Alright.app"), Path("/example/extension"), (), (), env={})


class PayloadQuarantineTests(unittest.TestCase):
    @staticmethod
    def appledouble(attributes):
        encoded = [(name.encode() + b"\0", value) for name, value in attributes]
        entries_size = sum((11 + len(name) + 3) & ~3 for name, value in encoded)
        data_start = 26 + 12 + 34 + 36 + entries_size
        data_length = sum(len(value) for name, value in encoded)
        total = data_start + data_length
        entries = bytearray()
        values = bytearray()
        for name, value in encoded:
            record = struct.pack(">IIHB", data_start + len(values), len(value), 0, len(name)) + name
            entries.extend(record + b"\0" * ((-len(record)) % 4))
            values.extend(value)
        header = struct.pack(">II16sH", 0x00051607, 0x00020000, b"\0" * 16, 1)
        finder_info = struct.pack(">III", 9, 38, total - 38) + b"\0" * 34
        attribute_header = struct.pack(">8I2H", 0x41545452, 0, total, data_start, data_length, 0, 0, 0, 0, len(encoded))
        return header + finder_info + attribute_header + entries + values

    @staticmethod
    def cpio_entry(name, data):
        name = name.encode() + b"\0"
        return (b"070707" + b"000000" * 7 + b"00000000000"
                + f"{len(name):06o}{len(data):011o}".encode() + name + data)

    def payload(self, entries, *, trailer=True):
        cpio = b"".join(self.cpio_entry(name, data) for name, data in entries)
        if trailer:
            cpio += self.cpio_entry("TRAILER!!!", b"")
        return io.BytesIO(gzip.compress(cpio))

    def test_clean_appledouble_values_do_not_trigger_substring_false_positive(self):
        metadata = self.appledouble([("com.apple.metadata:custom", b"com.apple.quarantine\0ordinary value")])
        payload = self.payload([("./Alright.app/Contents/MacOS/Alright", b"CODE"), ("./._Alright.app", metadata)])
        result = PACKAGE.validate_payload_quarantine(payload)
        self.assertEqual(result["appledouble_count"], 1)
        self.assertTrue(result["quarantine_absent"])

    def test_profile_appledouble_quarantine_is_rejected(self):
        metadata = self.appledouble([("com.apple.quarantine", b"TEST QUARANTINE VALUE")])
        for path in ("./Alright.app/Contents/._embedded.provisionprofile",
                     "./Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/._embedded.provisionprofile"):
            with self.subTest(path=path), self.assertRaisesRegex(PACKAGE.PackagingError, "payload quarantine"):
                PACKAGE.validate_payload_quarantine(self.payload([(path, metadata)]))

    def test_truncated_and_invalid_appledouble_metadata_is_rejected(self):
        valid = self.appledouble([("com.apple.metadata:custom", b"VALUE")])
        malformed_offset = bytearray(valid)
        struct.pack_into(">I", malformed_offset, 26 + 4, len(valid) + 1)
        for metadata in (b"NOT APPLEDOUBLE", valid[:-1], bytes(malformed_offset)):
            with self.subTest(metadata_length=len(metadata)), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_payload_quarantine(self.payload([("./._Alright.app", metadata)]))

    def test_truncated_payload_or_missing_trailer_is_rejected(self):
        for raw in (b"", b"070707", self.cpio_entry("./Alright.app/Contents/Info.plist", b"DATA")[:-1]):
            with self.subTest(raw_length=len(raw)), self.assertRaises(PACKAGE.PackagingError):
                PACKAGE.validate_payload_quarantine(io.BytesIO(gzip.compress(raw)))
        with self.assertRaises(PACKAGE.PackagingError):
            PACKAGE.validate_payload_quarantine(self.payload([("./Alright.app", b"")], trailer=False))

    def test_malformed_cpio_numeric_field_is_rejected(self):
        raw = bytearray(self.cpio_entry("./Alright.app", b""))
        raw[59:65] = b"XXXXXX"
        with self.assertRaises(PACKAGE.PackagingError):
            PACKAGE.validate_payload_quarantine(io.BytesIO(gzip.compress(bytes(raw))))


if __name__ == "__main__":
    # CTest may pass build/ for consistency with the other Python test suites.
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        sys.argv.pop(1)
    unittest.main()
