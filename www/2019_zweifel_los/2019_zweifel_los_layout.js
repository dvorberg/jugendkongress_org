document.observe('dom:loaded', function() {
    var body = $$("body")[0];
    if (mobile())
    {
        body.insert({top: '<div id="mobile-header"></div>'});
    }

    $("thema").insert({after: '<div id="waldweg"></div>'});

    $("waldweg").appendChild($("angebot"));
    $("waldweg").appendChild($("kongress"));
    // $("waldweg").appendChild($("anmeldung"));
    $("waldweg").appendChild($$("footer")[0]);
    
    var tops = $("waldweg").cumulativeOffset().top;
    $("waldweg").setStyle({position: "absolute",
                           top: (top + 40) + "px",
                           left: "0"});
    
    $("waldweg").insert({before: '<div id="waldweg-background"></div>'});
    
    $("waldweg").insert({before: '<div id="waldweg-img"></div>'});
    
    var header = $$("header")[0], site = $("site"),
        headerbg = $("headerbg");
    
    header.insert({top: '<h1>Zweifel los<span>!</span></h1>' +
                   '<h2>Zweifel zulassen, fühlen, bearbeiten</h2>'});
    headerbg.setStyle({height: header.getHeight() + "px"});
    
    if (mobile())
    {
        $("header-container").setStyle({top: "-"+(header.getHeight()+20)+"px"});
    }
    else
    {
        $("header-container").setStyle({height: header.getHeight() + "px"});
        $("waldweg").absolutize();
    }
    
    function adjust_positions(event) {        
        var vh = document.viewport.getHeight(),
            top = $("waldweg").viewportOffset().top,
            hh = header.getHeight(),
            m = vh - hh;
        
        if (mobile())
        {
            $("mobile-header").setStyle({height: m + "px"});
        }
        else
        {
            site.setStyle({marginTop: m + "px"});
        }
        
        if ( ! narrow() )
        {
            $("waldweg-background").setStyle(
                {position: "absolute",
                 top: ($("waldweg").cumulativeOffset().top-m) + "px",
                 left: "0",
                 width: "100%",
                 height: $("waldweg").getHeight() + "px"});            
            
            if (top <= vh)
            {
                if (top >= 0)
                {            
                    var diff = vh - top,
                        f = Math.abs(diff) / vh;
                }
                else
                {
                    f = 1.0;
                }
                
                $("waldweg-background").setStyle({opacity: f});
            }


            if (site.viewportOffset().top < 1)
            {
                var left = (document.viewport.getWidth() - header.getWidth())/2;
                if (left < 0) left = 0;
                header.setStyle({left: left + "px"});
                
                header.addClassName("sticky");
                headerbg.addClassName("sticky");
            }
            else
            {
                header.setStyle({left: 0});
                header.removeClassName("sticky");
                headerbg.removeClassName("sticky");
            }
        }
    };
    
    adjust_positions(null);
    document.observe("scroll", adjust_positions);
    Event.observe(window, "resize", adjust_positions);


    $$("div.workshop-link").each(function(div, counter) {
        div.observe("click", function(event) {
            var here = event.target;
            while(true)
            {
                var href = here.getAttribute("data-href");
                if (href)
                {
                    window.location.href = href;
                    break;
                }
                else
                {
                    here = here.parentNode;
                    if (here.tagName == "BODY")
                    {
                        throw "No data-href in workshop-link div";
                    }
                }
            }
        });
    });
});


jQuery(document).ready(function($) {
    setTimeout(function() {
        var $root = $('html, body');
        var href = window.location.href;
        var parts = href.split(/#/);
        var hh = $("#headerbg").height() + 14;

        if (parts.length > 1)
        {
            var id = parts[parts.length-1];
            id = decodeURIComponent(id);
            var sel = '#' + id;
            var $sel = $(sel);
            if ($sel.length > 0)
            {
                $root.animate({scrollTop: $sel.offset().top - hh}, 200);
                return false;
            }
        }
    }, 100);
});
