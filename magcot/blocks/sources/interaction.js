function toggleClass(button, groupName) {
	let fullGroupName = "g--" + groupName
	let groupElements = document.getElementsByClassName(fullGroupName)
	if (button.classList.contains("groupon")) {
		// the elements are visible now
		for (var i = 0; i < groupElements.length; ++i) {
			// hide the elements
			let el = groupElements[i]
			el.style.visibility = "hidden"
		}
		button.classList.remove("groupon")
		button.classList.add("groupoff")
	} else if (button.classList.contains("groupoff")) {
		// the elements are hidden now
		for (var i = 0; i < groupElements.length; ++i) {
			// show the elements
			let el = groupElements[i]
			el.style.visibility = "visible"
		}
		button.classList.remove("groupoff")
		button.classList.add("groupon")
	}
}


function prevTex() {
	if (texturePointer <= 0) {
		return
	}
	texturePointer -= 1
	refreshDisplayArea()
}


function nextTex() {
	if (texturePointer >= allTextures.length - 1) {
		return
	}
	texturePointer += 1
	refreshDisplayArea()
}


function refreshDisplayArea() {
	for (var i = 0; i < allTextures.length; ++i) {
		// hide all other texture wrappers
		let tex = allTextures[i]
		if (i == texturePointer) {
			tex.style.display = "block"
		} else {
			tex.style.display = "none"
		}
	}
	let texPath = JSON.parse(
		allTextures[texturePointer].getAttribute("data")).path
	if (texPath.length > 35) {texPath = texPath.slice(0, 34) + "…"}
	document.getElementById("texnameframe").innerText = texPath
	// display the texture path
	if (texturePointer <= 0) {
		// the first texture, render the `prev` button inactive
		document.getElementById("texprev").classList.remove("texon")
		document.getElementById("texprev").classList.add("texoff")
	} else {
		// render the `prev` button active
		document.getElementById("texprev").classList.remove("texoff")
		document.getElementById("texprev").classList.add("texon")
	}
	if (texturePointer >= allTextures.length - 1) {
		// similar as above, but for `next` button
		document.getElementById("texnext").classList.remove("texon")
		document.getElementById("texnext").classList.add("texoff")
	} else {
		document.getElementById("texnext").classList.remove("texoff")
		document.getElementById("texnext").classList.add("texon")
	}
}


function processId(idString, marker) {
	// used to generate the ID span in the info area
	// marker <=> content
	let segs = idString.split("--")
	// `Element` (at Python level) name and `Marker` name are separated
	// with "--"
	if (segs.length == 1) {
		return `<span class="markername">[${marker}]</span> `
			+ `<span class="pyelname">${segs[0]}</span>`
	} else {
		return `<span class="markername">[${marker}]</span> `
			+ `<span class="pyelname">${segs[0]}`
			+ `<span class="pymarkername">/${segs[1]}</span></span>`
	}
}


function processClickToCopy(content, type="coord") {
	if (type == "coord") {
		return `<div class="infocoord canbecopied">${content}</div>`
	} else if (type == "string") {
		return `<div class="infostring canbecopied">${content}</div>`
	}
}

function addCopiableListenersInInfo() {
	let canBeCopied = infoWindow.querySelectorAll(".canbecopied")
	for (var i = 0; i < canBeCopied.length; ++i) {
		let cbp = canBeCopied[i]
		addListener(cbp)
	}
}


function logPointInfo(el) {
	let data = JSON.parse(el.getAttribute("data"))
	let infoText = processId(el.id, el.innerText)
	infoText += ("\n<u>POSITION</u> = "
		+ processClickToCopy(`${data.x}, ${data.y}`))
	infoWindow.innerHTML = infoText
	addCopiableListenersInInfo()
}


function logPatchInfo(el) {
	let data = JSON.parse(el.getAttribute("data"))
	let infoText = processId(el.id, el.innerText)
	infoText += ("\n<u>UPPER-LEFT</u> = "
		+ processClickToCopy(`${data.x}, ${data.y}`))
	infoText += ("\n<u>SIZE</u> = "
		+ processClickToCopy(`${data.w}, ${data.h}`))
	infoWindow.innerHTML = infoText
	addCopiableListenersInInfo()
}


function logClippablePatchInfo(el) {
	let data = JSON.parse(el.getAttribute("data"))
	let infoText = processId(el.id, el.innerText)
	infoText += ("\n<u>UPPER-LEFT</u> = "
		+ processClickToCopy(`${data.x}, ${data.y}`))
	infoText += ("\n<u>SIZE</u> = "
		+ processClickToCopy(`${data.w}, ${data.h}`))
	infoText += ("\n<u>DIRECTION</u> = "
		+ processClickToCopy(`${data.direction}`, "string"))
	infoWindow.innerHTML = infoText
	addCopiableListenersInInfo()
}


function logGridInfo(el) {
	let data = JSON.parse(el.getAttribute("data"))
	let infoText = processId(el.id, el.innerText)
	infoText += ("\n<u>UPPER-LEFT</u> = "
		+ processClickToCopy(`${data.x}, ${data.y}`))
	infoText += ("\n<u>SIZE OF EACH CLIP</u> = "
		+ processClickToCopy(`${data.clip_w}, ${data.clip_h}`))
	infoText += ("\n<u>CLIP NUMBERS ALONG AXES</u> = "
		+ processClickToCopy(`${data.grid_x}, ${data.grid_y}`))
	infoWindow.innerHTML = infoText
	addCopiableListenersInInfo()
}