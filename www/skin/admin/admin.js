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

	//////////////////////////////////////////////////////////////////////
	
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

	class TableRowBasedController
	{
		get id()
		{
			if ( ! this.__id )
			{
				this.__id = this.row.getAttribute("data-id");
			}

			return this.__id;
		}

		get row()
		{
			if ( ! this.__row )
			{
				var here = this.node;
				while(here.tagName != "TR")
				{
					here = here.parentNode;
					if (here.tagName == "BODY") throw "Must be in <TR>.";
				}

				this.__row = here;
			}

			return this.__row;
		}

		modify_booking(what, dict, on_json_f=null)
		{
			modify_booking(this.id, what, dict,
						   this.on_json_fetched.bind(this));
		}

		on_json_fetched(result)
		{
			// pass
		}
	}
	
	class RoomOverwriteLinkController extends TableRowBasedController
	{
		constructor(a)
		{
			super();
		 
			this.a = a;
			this.room_span = a.parentNode.querySelector("span.room");
			this.a.addEventListener("click", this.on_click.bind(this));
		}

		get node()
		{
			return this.a;
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
			event.preventDefault();

			let newroom = prompt("Zimmer manuell festlegen (leer for keins)",
								 this.room_overwrite);
			if (newroom === null)
			{
				return;
			}
			else
			{
				this.modify_booking( "room_overwrite",
									 { room_overwrite: newroom });
			}

			return false;
		}

		on_json_fetched(result)
		{
			if (result.error)
			{
				alert(result.error);
			}
			else
			{
				if (result.room_overwrite)
				{
					this.room_span.innerHTML =
						result.room_overwrite.toUpperCase();
					this.room_span.classList.add("overwritten");
				}
				else
				{
					if (result.room)
					{
						this.room_span.innerHTML = result.room.toUpperCase();
					}
					else
					{
						this.room_span.innerHTML = "∅";
					}
					this.room_span.classList.remove("overwritten");
				}
			}
		}
	}
	
	document.querySelectorAll("a.room-overwrite-link").forEach( a => {
		new RoomOverwriteLinkController(a);
	});

	//////////////////////////////////////////////////////////////////////
	
	class RoleSelectController extends TableRowBasedController
	{
		constructor(select)
		{
			super();
			this.select = select;
			this.select.addEventListener("change", this.on_change.bind(this));
		}

		get node()
		{
			return this.select;
		}

		on_change(event)
		{
			const role = this.select.options[this.select.selectedIndex].value;
			this.modify_booking("role", {role: role});
		}

		on_json_fetched(result)
		{
			function set_role_class(element)
			{
				element.classList.remove("team");
				element.classList.remove("speaker");
				element.classList.remove("attendee");
				element.classList.add(result.role);
			}			
			set_role_class(this.select);
			const td = this.row.querySelector("td.role");
			set_role_class(td);
		}
	}

	document.querySelectorAll("select.role").forEach( a => {
		new RoleSelectController(a);
	});

	//////////////////////////////////////////////////////////////////////
	
	class HasPayedCheckboxController extends TableRowBasedController
	{
		constructor(input)
		{
			super();
			this.input = input;
			this.input.addEventListener("click", this.on_change.bind(this));
		}

		get node()
		{
			return this.input;
		}

		on_change(event)
		{
			this.modify_booking("has_payed", {has_payed: this.input.checked});
		}

		on_json_fetched(result)
		{
			this.row.classList.remove("table-danger");
			this.row.classList.remove("table-success");

			if (this.input.checked)
			{
				this.row.classList.add("table-success");
			}
			else
			{
				this.row.classList.add("table-danger");
			}
		}
	}

	document.querySelectorAll("input[name=has_payed]").forEach( a => {
		new HasPayedCheckboxController(a);
	});
	
	const paymend_dialog = document.querySelector("#payment-remarks-dialog");
	if (paymend_dialog)
	{
		const payment_modal = new bootstrap.Modal(paymend_dialog);

		paymend_dialog.querySelectorAll("button.close").forEach(button => {
			button.addEventListener("click", event => { payment_modal.hide(); })
		});
		
		class PaymentRemarksController extends TableRowBasedController
		{
			constructor(a)
			{
				super();
				this.a = a;
				this.a.addEventListener("click", this.on_click.bind(this));

				// add/remove EventListeners needs the listener to be identical.
				this.bound_on_save = this.on_save.bind(this);
			}

			get node()
			{
				return this.a;
			}

			get dialog_textarea()
			{
				return paymend_dialog.querySelector("textarea#payment-remarks");
			}

			get save_button()
			{
				return paymend_dialog.querySelector("button.save");
			}
			
			get span()
			{
				return this.row.querySelector("small.paymend-remarks");
			}
			
			on_click(event)
			{
				this.dialog_textarea.value = this.span.innerText;
				this.save_button.addEventListener("click", this.bound_on_save);
				
				payment_modal.show();
			}

			on_save(event)
			{			
				this.save_button.removeEventListener("click", this.bound_on_save);
				
				this.modify_booking("payment_remarks",
									{payment_remarks: this.dialog_textarea.value});
			}

			on_json_fetched(result)
			{
				payment_modal.hide();
				this.span.innerText = result.payment_remarks;
			}
		}

		document.querySelectorAll("a.edit-paymend-remarks").forEach( a => {
			new PaymentRemarksController(a);
		});
	}
	//////////////////////////////////////////////////////////////////////

	class FilterController
	{
		constructor(node)
		{
			this.node = node;

			const values = this.get_cookie_values(),
				  value = values[this.name];
			if (value)
			{
				this.value = value;
			}
			
			this.node.addEventListener("change", this.on_change.bind(this));
		}

		get name()
		{
			return this.node.getAttribute("data-filter-name");
		}

		get value()
		{
			throw "Not Implemented";
		}

		set value(value)
		{
			throw "Not Implemented";
		}

		get_cookie_values()
		{
			const cookie = get_cookie("filter") || "",
				  values = {};
			
			for(const part of cookie.split(","))
			{
				const pair = part.split("=");
				if (pair[0] && pair[1])
				{
					values[pair[0]] = pair[1];
				}
			}

			return values;
		}			
		
		on_change(event)
		{
			const values = this.get_cookie_values();
			
			values[this.name] = this.value;

			var new_cookie = "";
			for (const key in values)
			{
				if (values[key])
				{
					if (new_cookie) new_cookie += ",";
					new_cookie += key + "=" + values[key];
				}
			}

			set_cookie("filter", new_cookie);

			window.location.reload();
		}
	}

	class SelectFilterController extends FilterController
	{
		get value()
		{
			return this.node.options[this.node.selectedIndex].value;
		}

		set value(value)
		{
			for (var idx = 0; idx < this.node.options.length; idx++)
			{
				const option = this.node.options[idx];
				option.selected = (option.value == value);
			}
		}
	}

	class CheckboxFilterController extends FilterController
	{
		get value()
		{
			return this.node.checked;
		}

		set value(value)
		{
			if (value)
			{
				this.node.checked = true;
			}
			else
			{
				this.node.checked = false;
			}
		}
	}
	
	document.querySelectorAll("tbody.filters select").forEach( a => {
		new SelectFilterController(a);
	});
	document.querySelectorAll("tbody.filters input").forEach( a => {
		new CheckboxFilterController(a);
	});

	const reset_button = document.querySelector("tbody.filters button.reset");
	if (reset_button)
	{
		reset_button.addEventListener( "click", function (event) {
			set_cookie("filter", null);
			window.location.reload();
		});
	}
});
