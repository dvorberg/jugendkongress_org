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
});
