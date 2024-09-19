function findRatio() {
	// calculate the magnification ratio
	let maxWidth, maxHeight
	[maxWidth, maxHeight] = [256, 256]
	for (var i = 0; i < allTextures.length; ++i) {
		// find the max width and height among all the textures
		let tex = allTextures[i]
		let texData = JSON.parse(tex.getAttribute("data"))
		maxWidth = Math.max(maxWidth, texData.w)
		maxHeight = Math.max(maxHeight, texData.h)
	}
	// the ratio is 2 when the max size is smaller than 512x256; 1 if bigger.
	// however, the display window can only hold up to 1024x512
	if (maxWidth <= 512 && maxHeight <= 256) {
		magnification = 2 // global
		if (maxWidth > 256) {
			// stretch the display window!
			displayWindow.style.width = maxWidth * 2 + "px"
			displayArea.style.width = (maxWidth * 2 + 48) + "px"
			// 48 is the margin + padding of displayWindow
		}
	} else {
		magnification = 1 // global
		if (maxWidth > 512) {
			// also stretch the display window
			displayWindow.style.width = maxWidth + "px"
			displayArea.style.width = (maxWidth + 48) + "px"
		}
	}
}


function processTextures() {
	// resize all the <img> elements according to data provided by `texwrap`
	// and collect texture information
	for (var i = 0; i < allTextures.length; ++i) {
		let tex = allTextures[i]
		let texData = JSON.parse(tex.getAttribute("data"))
		texturePaths.push(texData.path)
		let texImg = tex.querySelector("img")
		texImg.style.width = magnification * texData.w + "px"
		texImg.style.height = magnification * texData.h + "px"
	}
}


function placeElements() {
	// place all the elements to where they should be
	for (var i = 0; i < allElements.length; ++i) {
		let el = allElements[i]
		let elData = JSON.parse(el.getAttribute("data"))
		el.style.zIndex = elData.z_index
	}
	for (var i = 0; i < allPoints.length; ++i) {
		// add point style
		let pn = allPoints[i]
		let pnData = JSON.parse(pn.getAttribute("data"))
		pn.style.left = "calc(" + magnification * pnData.x + "px - 0.85em)"
		pn.style.top = "calc(" + magnification * pnData.y + "px - 0.85em)"
		pn.style.backgroundColor = pnData.color
	}
	for (var i = 0; i < allAreas.length; ++i) {
		// add area style
		let ar = allAreas[i]
		let arData = JSON.parse(ar.getAttribute("data"))
		ar.style.left = magnification * arData.x + "px"
		ar.style.top = magnification * arData.y + "px"
		ar.style.borderColor = arData.color
		ar.style.color = arData.color
		ar.style.width = magnification * arData.w + "px"
		ar.style.height = magnification * arData.h + "px"
	}
	for (var i = 0; i < allGrids.length; ++i) {
		// correct grid patch sizes
		let grd = allGrids[i]
		let grdData = JSON.parse(grd.getAttribute("data"))
		let grdPatchWidth = grdData.clip_w * grdData.grid_x
		let grdPatchHeight = grdData.clip_h * grdData.grid_y
		grd.style.width = magnification * grdPatchWidth + "px"
		grd.style.height = magnification * grdPatchHeight + "px"
	}
}


function addGroupButtons() {
	// add buttons to toggle visibility of the group elements on the left
	for (let gn in allGroupData) {
		let groupButton = document.createElement("div")
		groupButton.classList.add("grouptoggler")
		groupButton.classList.add("groupon")
		groupButton.id = "btn--" + gn
		groupButton.innerText = gn
		groupButton.setAttribute("onclick", `toggleClass(this, '${gn}')`)
		let nEl = allGroupData[gn].length
		if (nEl > 9) {
			// the circle marker at the top-right corder can only display
			// one digit
			groupButton.setAttribute("elnumber", "…")
		} else {
			groupButton.setAttribute("elnumber", allGroupData[gn].length + "")
		}
		buttonField.appendChild(groupButton)
	}
}


function addListener(el) {
	el.addEventListener("click", () => {
		if (el.clickCooldown) {
			return
		}
		el.clickCooldown = true
		navigator.clipboard.writeText(el.innerText).then(() => {
			let originalText = el.innerHTML
			el.innerHTML = "<i>Copied.</i>"
			setTimeout(() => {
				el.innerHTML = originalText
				el.clickCooldown = false
			}, 250)
		})
	})
}


function addCopiableListeners() {
	// add event listeners to `.canbecopied` elements
	// when clicked, their inner texts will be copied
	let canBeCopied = document.querySelectorAll(".canbecopied")
	for (var i = 0; i < canBeCopied.length; ++i) {
		let cbp = canBeCopied[i]
		addListener(cbp)
	}
}


document.addEventListener(
	
	"DOMContentLoaded", () => {
		// these variables should be all global
		texturePointer = 0
		displayArea = document.getElementById("displayarea")
		displayWindow = document.getElementById("display")
		infoWindow = document.getElementById("info")
		buttonField = document.getElementById("buttonfield")
		allTextures = document.getElementsByClassName("texwrap")
		allElements = document.getElementsByClassName("element")
		allPoints = document.getElementsByClassName("point")
		allAreas = document.getElementsByClassName("area")
		allPatches = document.getElementsByClassName("patch")
		allCPatches = document.getElementsByClassName("cpatch")
		allGrids = document.getElementsByClassName("grid")
		texturePaths = []

		findRatio()
		processTextures()
		placeElements()
		addGroupButtons()
		refreshDisplayArea()
		addCopiableListeners()
	}

)