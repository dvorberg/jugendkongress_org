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

	const size_re = /\((\d+), (\d+)\)/;
	function on_resize()
	{
		document.querySelectorAll("div.archive a.og-image").forEach(a => {
			const img = a.querySelector("img"),
				  size_py = img && img.getAttribute("data-size"),
				  match = size_py && size_py.match(size_re),
				  card = a.parentNode;
			if (match)
			{
				const w = parseInt(match[1]),
					  h = parseInt(match[2]),
					  W = card.clientWidth,
					  H = W / w * h;

				a.style.width = W + "px";
				a.style.height = H + "px";
				
				// img.setAttribute("width", W);
				// img.setAttribute("height", H);
			}
		});
	}

	window.addEventListener("resize", on_resize);
	on_resize();
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


