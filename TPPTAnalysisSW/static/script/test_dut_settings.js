$(document).ready(function () {

    var postsuccess = function (data) {
        $("#Main").show()
        $("#loading").hide()
        location.reload(true)
    };

    var postfailure = function (data) {
        $("#Main").show()
        $("#loading").hide()
        $('.errormsg').text('Settings could not be saved. Please check the logs for details.')
        $('.errormsg').slideDown('fast')    
    };

    $('.setting_value_input').bind('input', function() {
        var text = $(this).val()
        if (text.indexOf(',') >= 0) {
            // Replace ',' with '.' -> allow comma decimal separator (e.g. Finnish locale)
            text = text.split(',').join('.');
        }

        var name = $(this).attr('name')

        // Check if the input text is a legal value for the input
        var valid = false
        if (name.match(/^offset/)) {
            // Allow negative and zero values
            if (text.match(/^-?\d+(\.\d+)?$/) && !isNaN(text)) {
                valid = true;
            }
        }
        else {
            // Do not allow negative or zero values
            if (text.match(/^\d+(\.\d+)?$/) && parseFloat(text) > 0) {
                valid = true;
            }
        }

        if (valid && $(this).hasClass('invalid')) {
            $(this).removeClass('invalid');
        }
        else if(!valid && !$(this).hasClass('invalid')) {
            $(this).addClass('invalid');
        }
    })

    $("#save_button").click(function () {
        // Check if there are invalid values
        if ($('.invalid').length > 0) {
            $('.errormsg').text('Please check the invalid values before saving')
            $('.errormsg').slideDown('fast')
        }
        else 
        {
            $("#Main").hide()
            $("#loading").show()

            $('.errormsg').hide();
            var saveValues = {};
            $('.setting_value_input').each(function() {
                saveValues[$(this).attr('name')] = $(this).val();
            });
            $('.setting_value_checkbox:checked').each(function() {
                saveValues[$(this).attr('name')] = $(this).val();
            });
            $('.dut_value_input').each(function () {
                saveValues[$(this).attr('name')] = $(this).val();
            });

            // Debug output
            //$('#output').text(JSON.stringify(saveValues, null, "  "));

            $.ajax({
                type: 'POST',
                data: {data: JSON.stringify(saveValues)},
                dataType: 'text'}).done(postsuccess).fail(postfailure);
        }      
    });
});

