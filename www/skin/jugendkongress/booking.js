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
	
	fetch_from_form(command, fields)
	{
		const url = controller_url + "/" + command + "booking",
			  data = new FormData();

		fields.forEach(field => {
			data.append(field, this.input_value(field));
		});

		fetch(url, { method: "post", body: data }).then(
			response => response.json()).then(
				this.on_fetched.bind(this));
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
	}

	on_email_blur(event)
	{
		this.fetch_from_form("create", [ "email" ]);
	}

	on_anmeldung_click(event)
	{
		console.log("ok");
	}

	on_fetched(result)
	{		
		if (result.status == "ok")
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
				}
				else
				{
					input.classList.add("is-valid");
					input.classList.remove("is-invalid");
				}
			}
		}
	}
}

window.addEventListener("load", function(event) {
	const div = document.querySelector("#anmelden-dialog");
	if (div)
		new AnmeldenDialogController(div);
})						
