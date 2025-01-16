window.addEventListener("load", function(event) {
    // Add the .table CSS class to every markdown table.
    document.querySelectorAll("div.markdown table").forEach(table => {
        for ( cls of [ "table", "table-hover", "table-bordered", "table-sm"] )
        {
            table.classList.add(cls);
        }

        table.querySelectorAll("tbody").forEach(tbody => {
            tbody.classList.add("table-group-divider");
        });
    });

	var counter = 1;
	const navbar = document.querySelector("header nav ul.navbar-nav");
	document.querySelectorAll("div.congress h2").forEach(h2 => {
		h2.setAttribute("id", `h${counter}`);

		const a = document.createElement("a");
		a.classList.add("nav-link");
		a.setAttribute("href", `#h${counter}`);
		a.appendChild(document.createTextNode(h2.textContent));
		
		const li = document.createElement("li");
		li.classList.add("nav-item");
		li.appendChild(a);

		navbar.appendChild(li);

		counter += 1;
	});

    function id_to_name(element)
    {
        if ( !element.hasAttribute("name") && element.hasAttribute("id") )
        {
            element.setAttribute(
                "name", element.getAttribute("id").replace(/-/g, "_"));
        }
    }
    document.querySelectorAll("form input").forEach(id_to_name);
    document.querySelectorAll("form textarea").forEach(id_to_name);
    document.querySelectorAll("form select").forEach(id_to_name);

	// This ought to be in a file names admin.js.
	// Why these have to go here, I know not. 
	function setCookie(name, value) {
		var expires = "";
		document.cookie = name + "=" + (value || "")  + expires + "; path=/";
	}
	function getCookie(name) {
		var nameEQ = name + "=";
		var ca = document.cookie.split(';');
		for(var i=0;i < ca.length;i++) {
			var c = ca[i];
			while (c.charAt(0)==' ') c = c.substring(1,c.length);
			if (c.indexOf(nameEQ) == 0)
				return c.substring(nameEQ.length,c.length);
		}
		return null;
	}
	function eraseCookie(name) {   
		document.cookie =
			name +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
	}
	
	const details_checkbox = document.querySelector("input#details");
	if (details_checkbox)
	{
		const state = getCookie("details");
		if (state !== null)
		{
			details_checkbox.checked = (state == "true");
		}
		
		details_checkbox.addEventListener("change", function(event) {
			setCookie("details", details_checkbox.checked);
			window.location.reload();
		});
	}
});

function send_user_email(login)
{
    fetch(portal_url + "/admin/forgott.py",
          {
              method: "POST", 
              body: "login=" + login,
              headers: { "Content-Type":
                             "application/x-www-form-urlencoded;charset=UTF-8"
                       },
          })
        .then(res => {
            alert("Es wurde eine e-Mail mit einem Passwort-Link an " +
                      login + " geschickt.");
        });
}


