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
		const url = controller_url + "/" + command + "booking",
			  data = new FormData();

		fields.forEach(field => {
			data.append(field, this.input_value(field));
		});

		for (var field in extra)
		{
			data.append(field, extra[field]);
		};

		if (on_json_f === null)
		{
			on_json_f = this.on_fetched.bind(this);
		}
		
		fetch(
			url, { method: "post", body: data }
		).then(
			response => {
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
	}

	on_email_blur(event)
	{
		this.fetch_from_form("create", [ "email" ], null, {"checkmail": true});
	}

	on_anmeldung_click(event)
	{
		this.fetch_from_form("create", [ "email", "firstname", "lastname" ]);
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
			alert("Die e-Mail mit deiner Buchung wurde erneut versendet." +
				  " Prüfe den Postfach.");
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

window.addEventListener("load", function(event) {
	const div = document.querySelector("#anmelden-dialog");
	if (div)
		new AnmeldenDialogController(div);
})						
