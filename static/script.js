
// access colors defined in css
var vars_from_css = getComputedStyle(document.body)
// .substring(1) removes first space in " #ff0000"
var gray_light = vars_from_css.getPropertyValue('--gray_light').substring(1);
var gray_dark = vars_from_css.getPropertyValue('--gray_dark').substring(1);
var green_light = vars_from_css.getPropertyValue('--green_light').substring(1);
var green_dark = vars_from_css.getPropertyValue('--green_dark').substring(1);
var red_light = vars_from_css.getPropertyValue('--red_light').substring(1);
var red_dark = vars_from_css.getPropertyValue('--red_dark').substring(1);

// points colors on the chart - UP/DOWN
var points_colors = [];
for (var x of predictions) {
    if (x == 'UP') {
        points_colors[points_colors.length] = green_light;
    } else if (x == 'DOWN') {
        points_colors[points_colors.length] = red_light;
    } else if (x == null) {
        points_colors[points_colors.length] = gray_light;
    }
}

// points borders colors on the chart
var points_borders = [];
for (var x of orders) {
    if (x == 'BUY') {
        points_borders[points_borders.length] = green_light;
    } else if (x == 'SELL') {
        points_borders[points_borders.length] = red_light;
    } else if (x == null) {
        points_borders[points_borders.length] = "transparent";
    }
}

new Chart("BTCUSD_chart", {
  type: "line",
  data: {
    labels: data_index,
    datasets: [{
      label: "Binance BTC/USDT_close_1h",
      fill: false,
      lineTension: 0,
      pointStyle: "circle",
      pointBackgroundColor: points_colors,
      pointStrokeColor: points_borders,
      pointBorderColor: points_borders,
      pointBorderWidth: 5,
      pointRadius: 2,
      borderWidth: 1,
      backgroundColor: gray_light,
      borderColor: gray_light,
      data: data_values
    }],
  },
  options: {
    responsive: true,
    legend: {
      display: false,
    },
    scales: {
      xAxes: [{
        gridLines: {
          color: gray_dark
        },
        ticks: {
            fontSize: 12,
            autoSkip: true,
            maxRotation: 90,
            minRotation: 70
        }
      }],
      yAxes: [{
        gridLines: {
          color: gray_dark
        },
        ticks: {
            fontSize: 12
        }
      }],
    },
    /*
    animation: {
      duration: 0,
    }
    */
  }
});


// texts colors
function set_tile_text_color(elementId, text_green, text_red)
{
    let element = document.getElementById(elementId)
    let content = element.textContent;
    if (content == text_green) {
        document.getElementById(elementId).style.color = green_light;
    }
    else if (content == text_red)
    {
        document.getElementById(elementId).style.color = red_light;
    }
}
set_tile_text_color("status", "Active", "Disabled");
set_tile_text_color("orders", "Allowed", "Disallowed");
set_tile_text_color("backups", "Allowed", "Disallowed");

function set_color_acc_pct(elementId)
{
    let element = document.getElementById(elementId)
    let content = element.textContent.slice(0, -1);  // removing % from 52.1%
    if (content > 50.0) {
        document.getElementById(elementId).style.color = green_light;
    }
    else if (content < 50.0)
    {
        document.getElementById(elementId).style.color = red_light;
    }
}
set_color_acc_pct("accuracy_pct");
set_color_acc_pct("accuracy_72h_pct");

function set_color_acc_text(elementId)
{
    let element = document.getElementById(elementId)
    let first_char = element.textContent.charAt(0);
    if (first_char == "+") {
        document.getElementById(elementId).style.color = green_light;
    }
    else if (first_char == "-")
    {
        document.getElementById(elementId).style.color = red_light;
    }
}
set_color_acc_text("accuracy_text");
set_color_acc_text("accuracy_72h_text");
set_color_acc_text("runtime_price_change_text");


// making logfile textarea scrolled to bottom by default
var textarea = document.getElementById('log_textarea');
textarea.scrollTop = textarea.scrollHeight;


// add breaks in textarea with some regex
var lines_broken = true;
var log_data = textarea.textContent;  // imported above
log_data_new = log_data.replace(/FILLED] /g,"FILLED]\n  ");  // /text/g flag makes replace work for all instances
log_data_new = log_data_new.replace(/ Try again/g,"\n  Try again");
function toggle_line_break() {
    if(lines_broken == false) {
        textarea.value = log_data;
        lines_broken = true;
        textarea.scrollTop = textarea.scrollHeight;
        document.getElementById("break_line_button").classList.add("button-clicked");
    }
    else if (lines_broken == true) {
        textarea.value = log_data_new;
        lines_broken = false;
        textarea.scrollTop = textarea.scrollHeight;
        document.getElementById("break_line_button").classList.remove("button-clicked");
    }
}
toggle_line_break()
