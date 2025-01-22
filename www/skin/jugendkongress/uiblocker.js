class UIBlocker
{
	constructor()
	{
		const self = this;
		this.blocked = false;

		Object.keys(window).forEach(key => {
			if (/^on(key|mouse)/.test(key)) {
				window.addEventListener(
					key.slice(2), this.on_event.bind(this));
			}
		});

		this.spinner = null;
		this.main_button = null;
		window.addEventListener("load", function(event) {
			self.spinner = document.querySelector("img#spinner");
			if (self.spinner) self.spinner.style.visibility = "hidden";
			self.main_button = document.querySelector("button.main");
			if (self.main_button) self.main_button.classList.remove("disabled");
		});
	}
	
	block()
	{
		if (this.blocked)
		{
			return;
		}
		else
		{
			this.blocked = true;
			document.body.classList.add("wait");
		}
		
		if (this.spinner) this.spinner.style.visibility = "visible";
		if (self.main_button) self.main_button.classList.add("disasbled");
	}

	unblock()
	{
		if (! this.blocked)
		{
			return;
		}
		else
		{
			this.blocked = false;
			document.body.classList.remove("wait");
		}
		
		if (this.spinner) this.spinner.style.visibility = "hidden";
		if (self.main_button) self.main_button.classList.remove("disabled");
	}

	on_event(event)
	{
		if (this.blocked)
		{
			event.preventDefault();			
		}
	}
}

const uiblocker = new UIBlocker();
