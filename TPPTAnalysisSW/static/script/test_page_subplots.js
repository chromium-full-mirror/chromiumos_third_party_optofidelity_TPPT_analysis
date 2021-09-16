// The amount of image loads currently in progress
var loadcount = 0

function imageLoaded() {
    loadcount -= 1;
    if (loadcount === 0) {
        $("#print_button").attr("disabled", false)
    }
}

function imageLoading() {
    loadcount += 1;
    if (loadcount === 1) {
        $("#print_button").attr("disabled", true)
    }
}

function showPlot(plotObject) {
    // plotObject is a (single) jQuery object for .plot instance
    if (!plotObject.data("shown")) {
        $.map($('.plot'), function(el) {
            var imgsrc = $(el).data("src");
            imageLoading();
            $(el).html("<img src=\"" + imgsrc + "\" onload=\"imageLoaded()\" />");
            $(el).data("shown", true);
        });
    }
}

function toggleState(set) {
    // Toggles the visibility state of given jQuery set
    set.each(function () { showPlot($(this)) });
    // Set the display value to same as the first one
    set.first().toggle();
    var display = set.css("display");
    set.css("display", display);
}

$(document).ready(function () {

    $(".all_lines_button").click(function () {
        // Select all plots
        var selector = ".plot"
        if ($(this).is("[data-target]")) {
            // Target defined
            selector = "#".concat($(this).attr("data-target")) + " " + selector
        }

        toggleState($(selector))
    });

    $(".failed_lines_button").click(function () {
        // Select failed plots
        var selector = `.${TestStatus.kFail} ~ .plot`
        if ($(this).is("[data-target]")) {
            // Target defined
            selector = "#".concat($(this).attr("data-target")) + " " + selector
        }

        toggleState($(selector))
    });

    $(".passed_lines_button").click(function () {
        // Select passed plots
        var selector = `.${TestStatus.kPass} ~ .plot`
        if ($(this).is("[data-target]")) {
            // Target defined
            selector = "#".concat($(this).attr("data-target")) + " " + selector
        }

        toggleState($(selector))
    });

    $(".subplot_table .show_plot").click(function () {
        showPlot($(this).parent().siblings(".plot"));
        $(this).parent().siblings(".plot").toggle();
    });
});
