const chartContainer = document.createElement("div")
const chartImg = document.createElement("img")
chartContainer.appendChild(chartImg)
const btnDisplatChart = document.getElementsByClassName("btn_display_chart")

Array.from(btnDisplatChart).forEach(elem => {
  elem.addEventListener("click", evt => {
    if (!(evt.currentTarget instanceof HTMLButtonElement)) {
      return
    }
    const sym = evt.currentTarget.dataset["symbol"]
    const src = `/chart/simple/${sym}`
    if(chartContainer.parentNode) {
      chartContainer.parentNode.removeChild(chartContainer)
    }
    chartImg.src = src
    evt.currentTarget.parentNode?.appendChild(chartContainer)
  })
})

