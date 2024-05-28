/* This file may be copyrighted. It has been obfuscated for brevity, not for secrecy. Check https://www.jugendkongress.org/layout.js?clear *//*
This file is part of the business logic for

  Jugendkongress

Copyright 2014 by Diedrich Vorberg <diedrich@tux4web.de>
Copyricht 2014 Jugendwerk der SELK <scharff@selk.de>

All Rights Reserved

The customer, JungePartner, Witten, is granted the right to use this
and all related sourcecode in running and maintaining above website
now and in the future. For this purpose it may be modified at
will. However, publication and commercial distribution is restricted
as for any other peace of proprietary software.

*/

jQuery(document).ready(function($) {
    var $root = $('html, body');
    $("a").click(function(){
        var href = $.attr(this, 'href');
        var parts = href.split(/#/);
        var hh = $("header").height();

        if (parts.length > 1)
        {
            var id = parts[parts.length-1];
            id = decodeURIComponent(id);
            var sel = '#' + id;
            var $sel = $(sel);
            if ($sel.length > 0)
            {
                $root.animate({scrollTop: $sel.offset().top - hh}, 500);
                return false;
            }
            else
            {
                window.location.href = href;
            }
        }
    });

    function update_gemeinde_alt_input_status()
    {
        var value = $("#anmeldeformular #gemeinde").val();

        if (value == "not-listed")
        {
            $("#gemeinde-alt").prop("disabled", false);
            $("#gemeinde-alt").prop("required", true);
            $("#gemeinde-alt").prop("placeholder", "Gemeinde");
            $("#gemeinde-alt").addClass("highlight");
        }
        else
        {
            $("#gemeinde-alt").prop("disabled", true);
            $("#gemeinde-alt").prop("required", false);
            $("#gemeinde-alt").prop("placeholder", "");
            $("#gemeinde-alt").removeClass("highlight");
        }
    }

    $("#anmeldeformular").change(update_gemeinde_alt_input_status);   
    
    update_gemeinde_alt_input_status();

    $("#anmeldeformular").submit(function(event) {
        var gemeinde = $("#anmeldeformular #gemeinde").val();
        if ( !gemeinde )
        {
            alert("Bitte wähle eine Gemeinde aus!");
            return false;
        }
        else if (gemeinde == "not-listed")
        {
            if ($("#gemeinde-alt") == "")
            {
                alert("Bitte gib den Namen Deiner Gemeinde ein!");
                $("#gemeinde-alt").focus();
                return false;
            }
        }

        return true;
    });


    function resize_iframes() {
        $("iframe").each(function(index, iframe) {
            var $iframe = $(iframe), width = $iframe.width();

            if ($iframe.hasClass("vertical"))
            {
                $iframe.height(width * 16 / 9);
            }
            else
            {
                $iframe.height(width * 9 / 16);
            }
        });
    }

    resize_iframes();
    $(window).resize(resize_iframes);        
    
});

// jQuery(document).ready(function($) {
//     var $root = $('html, body');
//     $("#mainmenu a").click(function(){
//         var href = $.attr(this, 'href');
//         var parts = href.split(/#/);
//         var sel = 'section#' + parts[parts.length-1];
//         var $sel = $(sel);
//         if ($sel.length > 0)
//         {
//             $root.animate({scrollTop: $sel.offset().top - 50}, 500);        
//             return false;
//         }
//         else
//         {
//             window.location.href = href;
//         }
//     });    
// });

function mobile() {
    // Returns true if we’re running on a mobile device (that doesn’t quite
    // support fixed backgrounds.
    return ( navigator.userAgent.match(/iPad|iPhone|Mobile|Android|BlackBerry|Kindle|Opera Mobi|Windows Phone/) !== null);
}

function narrow() {
    // Returns true if we’re running in responsive mode.
    return (document.viewport.getWidth() <= 812);
}

document.observe('dom:loaded', function() {
    if (mobile())
    {
        $$("body")[0].addClassName("mobile");
    }
    else
    {
        $$("body")[0].addClassName("desktop");
    }        
    
    if ($("anmeldeformular"))
    {
        $("anmeldeformular").show();
        $("anmeldeformular-javascript-warnung").hide();
    }
    
    $$("form [required=required]").each(function(input) {
        var here = input;
        while (here.tagName != "BODY" && ! here.hasClassName("control-group"))
        {
            here = here.parentNode;
        }

        if (here.hasClassName("control-group"))
        {
            var label = here.down(".control-label");
            var span = label.down("span");
            if (span)
            {
                span.addClassName("required");
            }
            else
            {
                label.innerHTML = '<span class="required">' + label.innerHTML + '</span>';
            }
        }
    });

    $$("form label.control-label").each(function(label) {
        var control_group = label.parentNode;
        var field_name = null;
        var required;
        
        if (label.getAttribute("data-field-name"))
        {
            field_name = label.getAttribute("data-field-name");
            required = "no";
        }
        else
        {
            var input = control_group.down("input");
            if (!input)
            {
                input = control_group.down("textarea");
            }

            if (input)
            {
                field_name = input.name;
            }
            else
            {
                // Can’t do anything.
                return;
            }
            
            required = "no";
            if (input.required)
            {
                required = "yes";
            }
        }
        
        var title = label.innerHTML.replace(/<.*>/g, "");
        control_group.insert({bottom:'<input type="hidden" name="titles:list" value="' + field_name + " " + required + " " + title + '" />'});
    });
});
