$(document).ready(function(){

    $('.alert').parent().hide();

    $(function() {
       $(document).on('click', '.alert-close', function() {
           $(this).parent().hide();
       });
    });

    var postsuccess = function (data) {
        $("#Main").show()
        $("#loading").hide()
        location.reload(true)
    };

    var postfailure = function (data) {
        progress.close();
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
        if (name.match(/^edgelimit/) || name.match(/^ztouchlimit/)) {
            // Allow negative and zero values
            if (text.match(/^-?\d+(\.\d+)?$/) && !isNaN(text)) {
                valid = true;
            }
        }
        //else if (name.match(/missing/)) {
        else {
            // Do not allow negative values
            if (text.match(/^\d+(\.\d+)?$/) && parseFloat(text) >= 0) {
                valid = true;
            }
        }
        /*
        else {
            // Do not allow negative or zero values
            if (text.match(/^\d+(\.\d+)?$/) && parseFloat(text) > 0) {
                valid = true;
            }
        }
        */

        if (valid && $(this).hasClass('invalid')) {
            $(this).removeClass('invalid');
        }
        else if(!valid && !$(this).hasClass('invalid')) {
            $(this).addClass('invalid');
        }
    });

    var progress;

    $("#save").on('submit', function(e) {

        // Check if there are invalid values
        e.preventDefault();

        if ($('.invalid').length > 0) {
            $('.errormsg').text('Please check the invalid values before saving');
            $('.errormsg').slideDown('fast');
        }
        else
        {

            if($("#save").context.activeElement.value === "recalculate") {
                $("#Main").hide();
                $("#loading").show();
            }

            var idvalues = [];
            $(".settings_table :input").each(function(){
                var idvalue = {id : $(this).attr("name"), value : $(this).val()};
                idvalues.push(idvalue);
            });


            if($("#save").context.activeElement.value === "recalculate") {

                progress  = new EventSource('/settings?event=progress');

                progress.onmessage = function(event) {
                    var val = Math.round(event.data * 100);
                    if(val <= 99) {
                        $('.prog').text(val);
                        $('.progress-bar').css('width', val + '%').attr('aria-valuenow', val);
                    } else {
                        $('.prog').text(100);
                        $('.progress-bar').css('width', 100 + '%').attr('aria-valuenow', 100);
                    }
                };

                $.ajax({
                    type: "POST",
                    url: "/settings",
                    data: {params: JSON.stringify(idvalues),
                           mode: $("#save").context.activeElement.value},
                    success : function(msg) {
                        progress.close();
                        location.reload(true);
                        $(document).ready(function() {
                            $('.alert').text(msg);
                            $('.alert').parent().show();
                            $('html, body').animate({ scrollTop: 0 }, 0);
                        });
                    }
                }).fail(postfailure);

            } else {

                $.ajax({
                    type: "POST",
                    url: "/settings",
                    data: {params: JSON.stringify(idvalues),
                           mode: $("#save").context.activeElement.value},
                   success : function(msg) {
                        $('.alert').text(msg);
                        $('.alert').parent().show();
                        $('html, body').animate({ scrollTop: 0 }, 0);
                    }
                }).fail(postfailure);

            }
        }

    });

});