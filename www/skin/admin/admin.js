window.addEventListener("load", function(event) {
	// Why the JavaScript spec does not contain this functionality is
	// beyond me.
	function set_cookie(name, value) {
		var expires = "";
		document.cookie = name + "=" + (value || "")  + expires + "; path=/";
	}
	
	function get_cookie(name) {
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
	
	class Checkbox
	{
		constructor(checkbox, active_colsets)
		{
			this.checkbox = checkbox;

			let colset = this.checkbox.getAttribute("value");
			if (colset)
			{
				this.colset = colset;
			}
			else
			{
				const label = this.checkbox.parentNode;
				this.colset = label.innerText.trim().toLowerCase();
			}

			this.checked = active_colsets.includes(this.colset);
		}

		get checked()
		{
			return this.checkbox.checked;
		}

		set checked(c)
		{
			this.checkbox.checked = c;
		}
	}

	class ColSetManager
	{
		constructor()
		{
			this.checkboxes = [];
			
			const inputs = document.querySelectorAll(
				"div.title input[type=checkbox]"),
				  details = this.get_details();
			
			for(const checkbox of inputs)
			{
				this.checkboxes.push(new Checkbox(checkbox, details));
				checkbox.addEventListener("change", this.on_change.bind(this));
			}
		}

		on_change(event)
		{
			set_cookie("details", this.cookie_value);
			window.location.reload();
		}
		
		get cookie_value()
		{
			let ret = [];
			this.checkboxes.forEach(cb => {
				if (cb.checked)
				{
					ret.push(cb.colset);
				}
			});
			return ret.join(",");
		}

		get_details()
		{
			const details = get_cookie("details");
			if ( ! details )
			{
				return [];
			}
			else
			{
				return details.split(",");
			}
		}
	}

	new ColSetManager();

	////////////////////////////////////////////////////////////

	function modify_booking(id, what, dict, on_json_f=null)
	{
		const url = portal_url + "/admin/modify_booking.py",
			  data = new FormData();

		data.append("id", id);
		data.append("what", what);
		for (var name in dict)
		{
			data.append(name, dict[name]);
		};		
			
		if (on_json_f === null)
		{
			on_json_f = function() {
				// pass
			}
		}
			
		fetch(
			url, { method: "post", body: data }
		).then(			
			response => {
				uiblocker.unblock();
					
				if (response.ok)
				{
					return response.json()
				}
				else
				{
					throw new Error(
						`Server Fehler! ${response.status} `
						`${response.statusText}`);
				}
			}
		).then(
			on_json_f
		).catch(err => {
			alert(err);
		});
	}

	class RoomOverwriteLinkController
	{
		constructor(a)
		{
			this.a = a;
			this.room_span = a.parentNode.querySelector("span.room");
			this.a.addEventListener("click", this.on_click.bind(this));

			var here = this.a;
			while(here.tagName != "TR")
			{
				here = here.parentNode;
				if (here.tagName == "BODY") throw "Must be in <TR>.";
			}
			this.id = here.getAttribute("data-id");
		}

		get room()
		{
			return this.room_span.innerText.trim();
		}

		get room_overwritten()
		{
			return this.room_span.classList.contains("overwritten");
		}

		get room_overwrite()
		{
			if (this.room_overwritten)
			{
				return this.room;
			}
			else
			{
				return "";
			}
		}
		
		on_click(event)
		{
			let newroom = prompt("Zimmer manuell festlegen (leer for keins)",
								 this.room_overwrite);
			if (newroom === null)
			{
				return;
			}
			else
			{
				this.send(newroom);
			}
		}

		send(newroom)
		{
			modify_booking( this.id, "room_overwrite",
							{ room_overwrite: newroom },
						    this.on_fetched.bind(this) );
		}

		on_fetched(result)
		{
			if (result.error)
			{
				alert(result.error);
			}
			else
			{
				if (result.room_overwrite)
				{
					this.room_span.innerHTML = result.room_overwrite;
					this.room_span.classList.add("overwritten");
				}
				else
				{
					this.room_span.innerHTML = result.room;
					this.room_span.classList.remove("overwritten");
				}
			}
		}
	}
	
	document.querySelectorAll("a.room-overwrite-link").forEach( a => {
		new RoomOverwriteLinkController(a);
	});
});
