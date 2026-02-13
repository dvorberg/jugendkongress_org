window.addEventListener("load", function(event) {
	document.querySelectorAll("form.rooms input[type=checkbox]").forEach(
		function(checkbox) {
			checkbox.addEventListener("click", function(event) {
				const room_no = checkbox.name,
					  booked = checkbox.checked ? "yes" : "",
					  url = portal_url +
					  "/admin/modify_room_booking.py?room_no=" + room_no +
					  "&booked=" + booked;
				
				uiblocker.block();
				
				fetch(url, { method: "get"}).then(			
					response => {
						uiblocker.unblock();
						
						if ( ! response.ok)
						{
							alert(`Server Fehler! ${response.status} `
								  `${response.statusText}`);
						}
					});
			});
		});
});
