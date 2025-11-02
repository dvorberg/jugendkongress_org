window.addEventListener("load", function(event) {
	function set_dark_scheme()
	{
		document.documentElement.setAttribute("data-bs-theme", "dark");
	}
	
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener(
		"change", set_dark_scheme);
});
