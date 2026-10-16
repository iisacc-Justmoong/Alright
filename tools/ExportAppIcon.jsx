// Run in Illustrator: File > Scripts > Other Script.
// Preserve edits to the native AI master; import SVG only on the first run.
#target illustrator
(function () {
    var root = File($.fileName).parent.parent;
    var assets = new Folder(root.fsName + "/resources/AppIcon");
    var report = new File(root.fsName + "/build/icon-review/illustrator-export.json");
    var previous = app.userInteractionLevel;
    try {
        var build = new Folder(root.fsName + "/build");
        if ((!build.exists && !build.create()) ||
            (!report.parent.exists && !report.parent.create())) {
            throw new Error("Unable to create the Illustrator export report directory.");
        }
        app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
        var nativeFile = new File(assets.fsName + "/Alright.ai");
        var input = nativeFile.exists ? nativeFile : new File(assets.fsName + "/Alright.svg");
        var doc = null;
        for (var i = 0; i < app.documents.length; i++) {
            try {
                if (app.documents[i].fullName.fsName === input.fsName) {
                    doc = app.documents[i];
                    break;
                }
            } catch (unnamedDocument) { /* Other unsaved documents remain untouched. */ }
        }
        if (!doc) { doc = app.open(input, DocumentColorSpace.RGB); }
        doc.activate();
        var bounds = doc.artboards[0].artboardRect;
        if (Math.abs(bounds[2] - bounds[0]) !== 1024 || Math.abs(bounds[1] - bounds[3]) !== 1024) {
            throw new Error("The vector master must have a 1024 by 1024 artboard.");
        }
        doc.artboards[0].name = "Alright — macOS 1024";
        if (doc.rasterItems.length !== 0 || doc.placedItems.length !== 0) {
            throw new Error("The icon must contain editable vectors only.");
        }
        var ai = new IllustratorSaveOptions();
        ai.pdfCompatible = true;
        ai.compressed = true;
        // Illustrator's SVG export changes the document's file identity.
        // Save the native AI immediately afterwards so it stays the open master.
        var svg = new ExportOptionsSVG();
        svg.embedRasterImages = false;
        svg.preserveEditability = false;
        svg.coordinatePrecision = 3;
        doc.exportFile(new File(assets.fsName + "/Alright.svg"), ExportType.SVG, svg);
        doc.saveAs(nativeFile, ai);
        var png = new ExportOptionsPNG24();
        png.antiAliasing = true;
        png.artBoardClipping = true;
        png.transparency = false;
        png.matte = false;
        png.horizontalScale = 100;
        png.verticalScale = 100;
        doc.exportFile(new File(assets.fsName + "/Alright"), ExportType.PNG24, png);
        if (!report.open("w")) { throw new Error("Unable to write the Illustrator export report."); }
        report.write('{"application":"Adobe Illustrator","version":"' + app.version + '","artboards":' + doc.artboards.length + ',"paths":' + doc.pathItems.length + ',"rasterItems":' + doc.rasterItems.length + ',"placedItems":' + doc.placedItems.length + ',"width":1024,"height":1024,"ai":"resources/AppIcon/Alright.ai","png":"resources/AppIcon/Alright.png"}');
        report.close();
        app.executeMenuCommand("fitin");
        app.redraw();
        doc.save();
    } catch (error) {
        if (report.open("w")) {
            report.write("ERROR: " + error.message + " at line " + error.line);
            report.close();
        }
        alert("Alright icon export failed: " + error.message);
    } finally {
        app.userInteractionLevel = previous;
    }
})();
