class BookingController
{
	constructor(div)
	{
		this.div = div;
	}
	
	input_value(name_or_id)
	{
		var input = this.div.querySelector("*[name=" + name_or_id + "]");
		if(!input)
		{
			input = this.div.querySelector("#" + name_or_id);
		}
		return input.value;
	}
	
	fetch_from_form(command, fields, on_json_f=null, extra={})
	{
		uiblocker.block();
		
		fields.forEach(field => {
			extra[field] = this.input_value(field);
		});

		this.send(command, extra, on_json_f);
	}

	send(command, dict, on_json_f=null)
	{
		const url = controller_url + "/" + command + "booking",
			  data = new FormData();
		
		for (var name in dict)
		{
			data.append(name, dict[name]);
		};		
		
		if (on_json_f === null)
		{
			on_json_f = this.on_fetched.bind(this);
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

	inputs()
	{
		return Array.from(this.div.querySelectorAll("input"));
	}
	
	on_fetched(result)
	{
		throw "Not Implemented";
	}
}

class AnmeldenDialogController extends BookingController
{
	constructor(div)
	{
		super(div);
		const self = this;		

		this.modal = new bootstrap.Modal(div);

		this.email_input = div.querySelector("input#email");
		this.email_input.addEventListener(
			"blur", this.on_email_blur.bind(this));
		this.anmelde_button = div.querySelector("#anmelde-button");
		this.anmelde_button.addEventListener(
			"click", this.on_anmeldung_click.bind(this));

		this.resend_help = div.querySelector("div#resend-email");
		this.resend_welcome_button = this.resend_help.querySelector("button");
		this.resend_welcome_button.addEventListener(
			"click", this.on_resend_welcome_button_click.bind(this));

		this.register_button = div.querySelector("#anmelde-button");

		this.div.querySelectorAll("input").forEach( input => {
			input.addEventListener("keyup", self.on_keyup.bind(self));
		});
	}
	
	on_email_blur(event)
	{
		this.fetch_from_form("create", [ "email" ], null, {"checkmail": true});
	}

	on_anmeldung_click(event)
	{
		this.fetch_from_form("create", [ "email", "firstname", "lastname" ]);
	}

	on_keyup(event)
	{
		if (event.keyCode == 13)
		{
			if (event.target.id == "email")
			{
				this.on_email_blur(event);
			}
			else
			{
				this.on_anmeldung_click(event);
			}
		}
	}

	on_fetched(result)
	{		
		if ( ! result.errors )
		{
			this.div.classList.add("was-validated");
		}
		else
		{
			this.div.classList.remove("was-validated");
		}

		for(const input of this.inputs())
		{
			const id = input.getAttribute("id");
			if (id in result.errors)
			{
				const message = result.errors[id];

				if (message)
				{
					input.classList.remove("is-valid");
					input.classList.add("is-invalid");

					const help = this.div.querySelector(
						"[data-for=" + id + "].invalid-feedback");
					if (help)
					{
						help.innerText = message;
					}

					if (id == "email")
					{
						this.register_button.classList.add("disabled");
					}					
				}
				else
				{
					input.classList.add("is-valid");
					input.classList.remove("is-invalid");

					if (id == "email")
					{
						this.register_button.classList.remove("disabled");
					}
				}
			}
		}

		if ("reveal-resend" in result)
		{
			this.resend_help.setAttribute("style", null);
		}

		if ("resent" in result)
		{
			this.modal.hide();

			setTimeout(function() {
				alert("Die e-Mail mit deiner Buchung wurde erneut versendet." +
					  " Prüfe den Postfach.");
			}, 100);
		}

		if("created" in result)
		{
			window.location.href = result.href;
		}
	}

	on_resend_welcome_button_click(event)
	{
		this.fetch_from_form("resend", [ "email" ]);
	}
}

class WorkshopController extends BookingController
{
	constructor(div, booking)
	{
		super(div);		
		const self = this;
		this.booking = booking;
		this.id = this.div.getAttribute("data-workshop-id");

		let footer = document.createElement("div"),
			innerdiv = document.createElement("div"),
			checkbox = document.createElement("input"),
			label = document.createElement("label");
		
		footer.classList.add("card-footer");
		footer.classList.add("form");

		innerdiv.classList.add("form-check");
		
		checkbox.classList.add("form-check-input");
		checkbox.type = "checkbox";
		checkbox.id = `checkbox-for-${this.id}`;

		label.classList.add("form-check-label");
		label.setAttribute("for", checkbox.id);
		label.innerText = "Vorauswahl";
		
		innerdiv.append(checkbox);
		innerdiv.append(label);

		footer.append(innerdiv)
		
		this.div.append(footer);

		this.footer = footer;
		this.checkbox = checkbox;

		this.header = this.div.querySelector(".card-header");

		this.checkbox.addEventListener(
			"click", this.on_checkbox_clicked.bind(this));
		
		Object.defineProperty(this, "selected", {
			set: function(selected)
			{
				if (selected)
				{
					this.send("drop-workshop-on-", { workshop_id: this.id });
				}
				else
				{
					this.send("select-workshop-on-", { workshop_id: this.id });
				}
			},

			get: function()
			{
				return this.checkbox.checked;
			}
		});

		this.checkbox.checked = booking.workshop_choices.includes(this.id);
		this.update_ui(this.checkbox.checked);
	}

	on_checkbox_clicked(event)
	{
		if (event.target.checked)
		{			
			const checkboxes = document.querySelectorAll(
				"div.workshop.card div.card-footer input[type=checkbox]");
			let counter = 0;
			checkboxes.forEach(checkbox => {
				if (checkbox.checked) counter++;
			});

			if (counter > 3)
			{
				alert("Du kannst nur drei Workshops vorauswählen. " +
					  "Es gibt ja auch nur drei Workshop-Phasen.");
				event.preventDefault();
				event.target.checked = false;
				return false;
			}
		}

		this.selected = ! event.target.checked;
	}

	update_ui(state)
	{		
		if (state)
		{
			this.div.classList.remove("border-primary");
			this.footer.classList.remove("bg-primary-subtle");
			this.div.classList.add("border-success");
			this.footer.classList.add("bg-success-subtle");
			this.header.classList.add("bg-success");
			this.header.classList.remove("bg-primary");
		}
		else
		{
			this.div.classList.remove("border-success");
			this.footer.classList.remove("bg-success-subtle");
			this.div.classList.add("border-primary");
			this.footer.classList.add("bg-primary-subtle");
			this.header.classList.remove("bg-success");
			this.header.classList.add("bg-primary");
		}
		
	}

	on_fetched(result)
	{
		this.update_ui(result.selected == this.id);
	}
}

class BookingFormController extends BookingController
{
	constructor(div, booking, errors)
	{
		super(div);
		const self = this;
		
		this.booking = booking;
		for (const field in booking)
		{
			const nn = field.replaceAll("_", "-");
			if (nn != field)
			{
				booking[nn] = booking[field];
			}
		}

		this.div.querySelectorAll("input").forEach(input => {
			if ( ["text", "email", "date", "time"].includes(input.type ))
			{
				input.addEventListener("blur", event => {
					self.send_from_input(input);
				});
				
				input.addEventListener("keyup", event => {
					self.dirty = true;
					
					self.div.classList.remove("was-validated");
					input.classList.remove("is-valid");
					input.classList.remove("is-invalid");
					
					if (event.keyCode == 13)
					{
						self.send_from_input(input);
					}
				});

				if (booking[input.id])
				{
					if (input.type == "text"
						|| input.type == "email"
						|| input.type == "time")
					{
						input.value = booking[input.id];
					}
					else if (input.type == "date")
					{
						input.value = booking[input.id].isoformat;
					}
				}
			}

			if (["radio", "checkbox"].includes(input.type))
			{
				input.addEventListener("click", event => {
					self.send_from_input(input);
				});

				const value = booking[input.name];
				if (value)
				{
					const selector =
						  `input[name=${input.name}][value="${value}"]`,
						  c = self.div.querySelector(selector);
					c.checked = true;
				}
			}			
		});
		
		this.div.querySelectorAll("textarea").forEach(input => {
			input.addEventListener("blur", event => {
				self.send_from_input(input);
			});
			input.addEventListener("keyup", event => {
				self.dirty = true;
				input.classList.remove("is-valid");
				input.classList.remove("is-invalid");
			});
			input.value = booking[input.id] || "";
		});			
		
		this.report_errors(errors);

		this.save_button = this.div.querySelector("#save-button");
		Object.defineProperty(this, "dirty", {
			set: function(dirty) {
				this._dirty = dirty;

				if (dirty)
				{
					this.save_button.classList.add("btn-primary");
					this.save_button.classList.remove("btn-success");
				}
				else
				{
					this.save_button.classList.remove("btn-primary");
					this.save_button.classList.add("btn-success");
				}
			},
			get: function()
			{
				return this._dirty;
			}
		});
		this.dirty = false;		
		window.addEventListener("beforeunload",
								this.on_beforeunload.bind(this));

		document.querySelectorAll("div.workshop.card").forEach(div => {
			new WorkshopController(div, this.booking);
		});

		this.update_travel_if();
	}

	update_travel_if()
	{
		const active = this.div.querySelector(
			'input[name=mode_of_travel]:checked').value;
		if (active == "null")
		{
			this.div.querySelector("div.road-travel").style="display:none";
			this.div.querySelector("div.rail-travel").style="display:none";
		}
		else if (active == "car")
		{
			this.div.querySelector("div.road-travel").style="display:block";
			this.div.querySelector("div.rail-travel").style="display:none";
		}
		else if (active == "rail")
		{
			this.div.querySelector("div.road-travel").style="display:none";
			this.div.querySelector("div.rail-travel").style="display:block";
		}
	}
	

	on_beforeunload(event)
	{
		const ae = document.activeElement;
		if (["INPUT", "TEXTAREA"].includes(ae.tagName) && this.dirty)
		{
			document.activeElement.blur();
			event.preventDefault();
			event.returnValue = true;
			return true;
		}
	}

	send_from_input(input)
	{
		const change = {};

		if (["text", "email", "date", "time"].includes(input.type))
		{
			change[input.id || input.name] = input.value;
		}
		else if (input.type == "radio")
		{
			change[input.name] = input.value;
			this.update_travel_if();
		}
		else if (input.type == "checkbox")
		{
			change[input.id] = input.checked;
		}
		else if (input.tagName == "TEXTAREA")
		{
			change[input.id] = input.value;
		}

		this.send("modify", change);
		this.dirty = false;
	}

	on_fetched(result)
	{
		this.report_errors(result.errors);
	}
	
	report_errors(errors)
	{
		for (const field in errors)
		{			
			const inputs = new Array();
			this.div.querySelectorAll("#" + field).forEach(
				input => { inputs.push(input)});
            this.div.querySelectorAll(`input[name="${field}"]`).forEach(
				input => { inputs.push(input)} );

			
			const help = this.div.querySelector(
				"[data-for=" + field + "].invalid-feedback");

			if (errors[field])
			{			
				if (inputs)
				{
					inputs.forEach(input => {
						input.classList.remove("is-valid");
						input.classList.add("is-invalid");
					});
				}
				
				if (help)
				{
					help.innerText = errors[field];
					help.style.display = "block";
				}
			}
			else
			{
				inputs.forEach(input => {
					input.classList.add("is-valid");
					input.classList.remove("is-invalid");
				});
				if (help)
				{
					help.style.display = "none";
				}
			}
		}
	}
}


      
window.addEventListener("load", function(event) {
    const dialog = document.querySelector("#anmelden-dialog");
    if (dialog) new AnmeldenDialogController(dialog);

    const form = document.querySelector("#booking");
	if (form) new BookingFormController(form, booking, booking_errors);
});
