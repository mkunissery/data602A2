var resizefunc = [];
var $ = jQuery;
var jSellValue = 0
$(document).ready(function(){

    //Handle Buy/Sell Tabs
    $("#tabs").tabs();

    // By Default

    //Positions
    $.ajax({url: "http://127.0.0.1:5000/Positions", success: function(result){
        var data = result.replace(/&lt;/g,"<").replace(/&gt;/g,">")
        $("#OpenPositions").html(data);
        $.ajax({url: "http://127.0.0.1:5000/Summary", success: function(result){
            var jrarr = result.split('~')
            $("#portfoliovalue").html("<b>" + jrarr[0] + "</b>");
            $("#cashvalue").html("<b>" + jrarr[1] + "</b>");
            $("#totalreturn").html("<b>" + jrarr[2] + "</b>");
             }});
    }});


    //Load Pie
    $.ajax({url: "http://127.0.0.1:5000/Getpie", success: function(jdata){

        Highcharts.chart('piechart', {
            chart: {
                plotBackgroundColor: null,
                plotBorderWidth: null,
                plotShadow: false,
                type: 'pie'
            },
            title: {
                text: 'Investment Allocation by % Total'
            },
            tooltip: {
                pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
            },
            plotOptions: {
                pie: {
                    allowPointSelect: true,
                    cursor: 'pointer',
                    dataLabels: {
                        enabled: true,
                        format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                        style: {
                            color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                        }
                    }
                }
            },
            series: [{
                name: 'Position %',
                data:JSON.parse(jdata),
                colorByPoint: true
            }]
        });
    }});



    //load intraday first time
    $.ajax({url: "http://127.0.0.1:5000/GetPriceStat/BTC"   , success: function(result){
        var jloadintraday = ""
        var jArr = result.split("~")
        $("#manual_buy_price").val(jArr[0]);
        $("#statcurr").text(jArr[0]);
        $("#statmax").text(jArr[1]);
        $("#statmin").text(jArr[2]);
        $("#statavg").text(jArr[3]);
        $("#statstdev").text(jArr[4]);

        $("#statcurrsell").text(jArr[0]);
        $("#statmaxsell").text(jArr[1]);
        $("#statminsell").text(jArr[2]);
        $("#statavgsell").text(jArr[3]);
        $("#statstdevsell").text(jArr[4]);
        jloadintraday =jArr[5]

        var idaychart = new  Highcharts.stockChart('intraday', {
            xAxis: {
                type: 'datetime',
                labels: {
                    formatter: function() {
                        return Highcharts.dateFormat('%d/%m %H:%M', this.value);
                    }
                }
            },

            rangeSelector : {
                enabled: false
            },
            navigator: {
                enabled: false
            },


            title: {
                text:  'BTC Price - Last 24 Hours'
            },

            width:250,

            series: [{
                name: 'BTC',
                data: JSON.parse(jloadintraday)

            }]
        });

        var content = $("#intraday").html();
        $("#intradaysell").html(content)

        $.ajax({url: "http://127.0.0.1:5000/Getmessagelog", success: function(result){
            $("#messagelog").html(result);
        }});

    }});
    // end by default load


    //Tradelog
    $.ajax({url: "http://127.0.0.1:5000/Tradelog", success: function(result){
        $("#tradelog").html(result);
    }});



    //Populate Buy Coin List
    $.ajax({url: "http://127.0.0.1:5000/GetCryptoList", success: function(result){
        var jintraydaydata = ""
        $("#tradelist").html = ""
        $("#tradelist").html(result);
        $('#manual_buy_target').bind('change', function() {
            var jcoin = $('#manual_buy_target').find(":selected").val()
            var jcoindesc = jcoin.split("(")
            var jcoinname = jcoindesc[0].trim()
            var jcoinsym = jcoindesc[1].toUpperCase().slice(0,-1)
            $("#buycoin").html(jcoinsym);
            $.ajax({
                url: "http://127.0.0.1:5000/GetPriceStat/" + jcoinsym, success: function (result) {
            
                   
                    if (result != "") {
                        var jArr = result.split("~")
                        $("#manual_buy_price").val(jArr[0]);
                        $("#statcurr").text(jArr[0]);
                        $("#statmax").text(jArr[1]);
                        $("#statmin").text(jArr[2]);
                        $("#statavg").text(jArr[3]);
                        $("#statstdev").text(jArr[4]);
                        jintraydaydata = jArr[5]
                        var jdollar = $("#manual_buy_total").val()
                        var junits = jdollar / parseFloat(result)
                        $("#manual_buy_amount").val(junits)
                        $("#buysummary").html("You are buying <B>" + precisionRound(parseFloat(junits), 4) + "</B> " + jcoinsym + " at <B>$" + precisionRound(parseFloat(result), 4) + "</b> per <B>" + jcoinsym + "</b>");

                        //temp chart begin : intraday buy on change of coin list


                        var idaychart = new Highcharts.stockChart('intraday', {
                            xAxis: {
                                type: 'datetime',
                                labels: {
                                    formatter: function () {
                                        return Highcharts.dateFormat('%d/%m %H:%M', this.value);
                                    }
                                }
                            },

                            rangeSelector: {
                                enabled: false
                            },
                            navigator: {
                                enabled: false
                            },


                            title: {
                                text: jcoinname + ' Price - Last 24 Hours'
                            },

                            width: 250,

                            series: [{
                                name: jcoinsym,
                                data: JSON.parse(jintraydaydata)

                            }]
                        });

                    }
                    else
                    {
                        alert("Price not available for" + jcoin + ". Please try after sometime.")
                        $("#manual_buy_price").selectedIndex = 0
                    }

                //temp chart end

            }});




            $.ajax({url: "http://127.0.0.1:5000/Getmultiseries/" +jcoinsym, success: function (data) {
                // Create the chart
                var arrname = [jcoinsym,jcoinsym + "-20D SMA"];
                arrdata = data.split("~")


                Highcharts.stockChart('Chartmult', {

                    xAxis: {
                        type: 'datetime',
                        labels: {
                            formatter: function() {
                                return Highcharts.dateFormat('%m/%d/%y', this.value);
                            }
                        }
                    },

                    rangeSelector : {
                        inputEnabled:false
                    },

                    title: {
                        text: 'Historical ' + jcoinname + ' Price vs 20D SMA'
                    },

                    width:250,

                    tooltip: {
                        pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>',
                        valueDecimals: 2,
                        split: true
                    },

                    series: [
                        {
                            color:'rgb(191, 63, 63)',
                            name: arrname[0],
                            data: JSON.parse(arrdata[0])
                        },
                        {
                            color:'rgb(63,127,191)',
                            name: arrname[1],
                            data: JSON.parse(arrdata[1])
                        }

                    ]
                });
            }});




        });

    }});


    //Populate Sell Coin List
    $.ajax({url: "http://127.0.0.1:5000/Active", success: function(result){
        var jintradayselldata = ""
        $("#selltradelist").html = ""
        $("#selltradelist").html(result)

        $('#manual_sell_target').bind('change', function() {
            $("#sellsummary").html(" ")
            $('#manual_sell_total').val("")
            var jcoin = $('#manual_sell_target').find(":selected").val()
            var jcoindesc = jcoin.split("(")
            var jcoinname = jcoindesc[0].trim()
            var jcoinsym = jcoindesc[1].toUpperCase().slice(0,-1)
            $("#sellcoin").html(jcoinsym)

            $.ajax({url: "http://127.0.0.1:5000/Shares/" + jcoinsym , success: function(result){
                jSellValue = parseFloat(result)
                $("#maxsellshares").text(" max:(" + precisionRound(parseFloat(result),4) + ")");
            }});


            $.ajax({url: "http://127.0.0.1:5000/GetPriceStat/" + jcoinsym , success: function(result){
                var jArr = result.split("~")
                $("#manual_sell_price").val(jArr[0]);
                $("#statcurrsell").text(jArr[0]);
                $("#statmaxsell").text(jArr[1]);
                $("#statminsell").text(jArr[2]);
                $("#statavgsell").text(jArr[3]);
                $("#statstdevsell").text(jArr[4]);
                jintradayselldata = jArr[5].trim()


                var idaychart = new  Highcharts.stockChart('intradaysell', {
                    xAxis: {
                        type: 'datetime',
                        labels: {
                            formatter: function() {
                                return Highcharts.dateFormat('%d/%m %H:%M', this.value);
                            }
                        }
                    },

                    rangeSelector : {
                        enabled: false
                    },
                    navigator: {
                        enabled: false
                    },


                    title: {
                        text:  jcoinname + ' Price - Last 24 Hours'
                    },

                    width:250,

                    series: [{
                        name:jcoinsym,
                        data: JSON.parse(jintradayselldata)

                    }]
                });

            }});




            //temp chart end



            $.ajax({url: "http://127.0.0.1:5000/Getmultiseries/" +jcoinsym, success: function (data) {
                // Create the chart
                var arrname = [jcoinsym,jcoinsym + "-20D SMA"];
                arrdata = data.split("~")


                Highcharts.stockChart('Chartmult', {

                    xAxis: {
                        type: 'datetime',
                        labels: {
                            formatter: function() {
                                return Highcharts.dateFormat('%m/%d/%y', this.value);
                            }
                        }
                    },

                    rangeSelector : {
                        inputEnabled:false
                    },

                    title: {
                        text: 'Historical ' + jcoinname + ' Price vs 20D SMA'
                    },

                    width:250,

                    tooltip: {
                        pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> <br/>',
                        valueDecimals: 2,
                        split: true
                    },

                    series: [
                        {
                            color:'rgb(191, 63, 63)',
                            name: arrname[0],
                            data: JSON.parse(arrdata[0])
                        },
                        {
                            color:'rgb(63,127,191)',
                            name: arrname[1],
                            data: JSON.parse(arrdata[1])
                        }

                    ]
                });
            }});

        });
    }});

    $.ajax({url: "http://127.0.0.1:5000/Getcash", success: function(result){
        $("#cashpos").text("Cash :$"+ precisionRound(result,2));
    }});



});




$('#manual_sell_total').change(function() {
    $("#sellsummary").html(" ")
    var jUnits =  $('#manual_sell_total').val()

    var jcoin = $('#manual_sell_target').find(":selected").val()
    var jcoindesc = jcoin.split("(")
    var jcoinname = jcoindesc[0].trim()
    var jcoinsym = jcoindesc[1].toUpperCase().slice(0,-1)
    var shareprice = $("#manual_sell_price").val()

    if(jUnits > jSellValue){

        alert("You do not have enough shares to sell.")
        $('#manual_sell_total').val("")
        return false
    }

    if(parseFloat(jUnits) > 0)
    {
        $("#sellsummary").html("Sell " + jUnits + " shares of <b>" + jcoinsym + "</b> at a price of <b>" + shareprice + "</b> for an estimated <b>$" + String(precisionRound(parseFloat(shareprice)*parseFloat(jUnits),2))  + "</b>")
    }

});


$('#manual_buy_total').change(function() {
    var jDollar =  $('#manual_buy_total').val()
    if(parseFloat(jDollar) > 0)
    {
        if( $('#manual_buy_target').find(":selected").val() != "-1")
            $("#manual_buy_target").change();
    }
});


$('#placingBuyOrderButton').click(function() {

    //Check for cash first.
    var javailcash = 0;
    $.ajax({

        url: "http://127.0.0.1:5000/Getcash",
        success: function(result){
            javailcash = parseFloat(result)
            $("#cashpos").text("Cash :$"+ javailcash);



            var jcoin = $('#manual_buy_target').find(":selected").val()
            var jcoindesc = jcoin.split("(")
            var jcoinname = jcoindesc[0].trim()
            var jcoinsym = jcoindesc[1].toUpperCase().slice(0,-1)
            var jdollar = $("#manual_buy_total").val()

            if(javailcash < jdollar)
                alert("Sorry !. you do not have enough funds to place this order.")

            else
            {

                $.ajax({url: "http://127.0.0.1:5000/PlaceTrade/?ticker=" + jcoinname + "&amount=" + jdollar +"&symbol=" + jcoinsym + "&ttype=B", success: function(result){

                    alert("Trade Sucessfully executed at price:" + result)
                }});

                $("#tradelog").html('<img src="http://127.0.0.1:5000/static/img/loading1.gif">');
                $("#OpenPositions").html('<img src="http://127.0.0.1:5000/static/img/loading1.gif">');
                $("#piechart").html('<img src="http://127.0.0.1:5000/static/img/loading1.gif">');

                $.ajax({url: "http://127.0.0.1:5000/Getcash", success: function(result){
                    $("#cashpos").text("Cash :$"+result);
                }});

                $.ajax({url: "http://127.0.0.1:5000/Tradelog", success: function(result){
                    $("#tradelog").html(result);
                }});
                $.ajax({url: "http://127.0.0.1:5000/Positions", success: function(result){
                    var posdata = result.replace(/&lt;/g,"<").replace(/&gt;/g,">")
                    $("#OpenPositions").html(posdata);
                    $.ajax({
                        url: "http://127.0.0.1:5000/Summary", success: function (result) {
                            var jrarr = result.split('~')
                            $("#portfoliovalue").html("<b>" + jrarr[0] + "</b>");
                            $("#cashvalue").html("<b>" + jrarr[1] + "</b>");
                            $("#totalreturn").html("<b>" + jrarr[2] + "</b>");
                        }
                    });
                }});

                //Load Pie
                $.ajax({url: "http://127.0.0.1:5000/Getpie", success: function(jdata){
                    Highcharts.chart('piechart', {
                        chart: {
                            plotBackgroundColor: null,
                            plotBorderWidth: null,
                            plotShadow: false,
                            type: 'pie'
                        },
                        title: {
                            text: 'Investment Allocation by % Total'
                        },
                        tooltip: {
                            pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
                        },
                        plotOptions: {
                            pie: {
                                allowPointSelect: true,
                                cursor: 'pointer',
                                dataLabels: {
                                    enabled: true,
                                    format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                                    style: {
                                        color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                                    }
                                }
                            }
                        },
                        series: [{
                            name: 'Position %',
                            data:JSON.parse(jdata),
                            colorByPoint: true
                        }]
                    });
                }});
                $('#manual_sell_target').append($('<option>', {
                    value: jcoin,
                    text: $('#manual_buy_target').find(":selected").text()
                }));

                //populate message log after trade.
                $.ajax({
                    url: "http://127.0.0.1:5000/Getmessagelog", success: function (result) {
                        $("#messagelog").html(result);
                    }
                });

            }

        }});




});


//placingsellOrderButton

$('#placingsellOrderButton').click(function() {


    var jcoin = $('#manual_sell_target').find(":selected").val()
    if(jcoin == "-1")
    {
        alert("select a coin to sell.")
        return false

    }
    var jcoindesc = jcoin.split("(")
    var jcoinname = jcoindesc[0].trim()
    var jcoinsym = jcoindesc[1].toUpperCase().slice(0,-1)
    var qty = $('#manual_sell_total').val()

    if(qty == "") {
        alert("Enter the number of shares to sell")
        return false
    }

    if(qty > jSellValue){

        alert("You do not have enough shares to sell.")
        return false
    }


    $.ajax({
        url: "http://127.0.0.1:5000/PlaceTrade/?ticker=" + jcoinname + "&qty=" + qty + "&symbol=" + jcoinsym + "&ttype=S", success: function (result) {

        alert("Trade Sucessfully executed at price:" + result)
        $.ajax({url: "http://127.0.0.1:5000/Tradelog", success: function(result){
            $("#tradelog").html(result);
        }});
        $.ajax({url: "http://127.0.0.1:5000/Positions", success: function(result){
            var posdata = result.replace(/&lt;/g,"<").replace(/&gt;/g,">")
            $("#OpenPositions").html(posdata);
            $.ajax({
                url: "http://127.0.0.1:5000/Summary", success: function (result) {
                    var jrarr = result.split('~')
                    $("#portfoliovalue").html("<b>" + jrarr[0] + "</b>");
                    $("#cashvalue").html("<b>" + jrarr[1] + "</b>");
                    $("#totalreturn").html("<b>" + jrarr[2] + "</b>");
                }
            });
        }
        });

        $.ajax({
            url: "http://127.0.0.1:5000/Getcash", success: function (result) {
                $("#cashpos").text("Cash :$" + result);
            }
        });

        //Load Pie
        $.ajax({
            url: "http://127.0.0.1:5000/Getpie", success: function (jdata) {
                Highcharts.chart('piechart', {
                    chart: {
                        plotBackgroundColor: null,
                        plotBorderWidth: null,
                        plotShadow: false,
                        type: 'pie'
                    },
                    title: {
                        text: 'Investment Allocation by % Total'
                    },
                    tooltip: {
                        pointFormat: '{series.name}: <b>{point.percentage:.1f}%</b>'
                    },
                    plotOptions: {
                        pie: {
                            allowPointSelect: true,
                            cursor: 'pointer',
                            dataLabels: {
                                enabled: true,
                                format: '<b>{point.name}</b>: {point.percentage:.1f} %',
                                style: {
                                    color: (Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black'
                                }
                            }
                        }
                    },
                    series: [{
                        name: 'Position %',
                        data: JSON.parse(jdata),
                        colorByPoint: true
                    }]
                });
            }
        });

        //populate message log after trade.
        $.ajax({
            url: "http://127.0.0.1:5000/Getmessagelog", success: function (result) {
                $("#messagelog").html(result);
            }
        });

        //update

    }});

   


});

//first time highchart
$.ajax({url: "http://127.0.0.1:5000/Getmultiseries/BTC", success: function (data) {
    // Create the chart
    var arrname = ["BTC","BTC-20D SMA"];
    arrdata = data.split("~")


    Highcharts.stockChart('Chartmult', {

        xAxis: {
            type: 'datetime',
            labels: {
                formatter: function() {
                    return Highcharts.dateFormat('%m/%d/%y', this.value);
                }
            }
        },

        rangeSelector : {
            inputEnabled:false
        },

        title: {
            text: 'Historical Bitcoin Price'
        },

        width:250,

        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.change}%)<br/>',
            valueDecimals: 2,
            split: true
        },

        series: [
            {
                color:'rgb(191, 63, 63)',
                name: arrname[0],
                data: JSON.parse(arrdata[0])
            },
            {
                color:'rgb(63,127,191)',
                name: arrname[1],
                data: JSON.parse(arrdata[1])
            }

        ]
    });
}});

//end firsttime highchart





function precisionRound(number, precision) {
    var factor = Math.pow(10, precision);
    return Math.round(number * factor) / factor;
}

function ChartIt(symbol)
{
    PlotNewCharts("WAP", "Historical VWAP of " + symbol, symbol)
}

function PlotNewCharts(charttype, title, symbol)
{
    var addtouri = ""
    if(symbol != "")
        addtouri = "&coin=" + symbol 
    var sUri = "http://127.0.0.1:5000/hpl1/?measure=" +charttype + addtouri

    $.ajax({url:  sUri, success: function (data) {
        // Create the chart
        if(data == "") 
        {
            alert("No data to plot.")
            return false
        }
        Highcharts.stockChart('Chartmult', {

            xAxis: {
                type: 'datetime',
                labels: {
                    formatter: function() {
                        return Highcharts.dateFormat('%m/%d/%y', this.value);
                    }
                }
            },

            rangeSelector : {
                inputEnabled:false
            },

            title: {
                text: title
            },

            width:250,

            tooltip: {
                pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>',
                valueDecimals: 2,
                split: true
            },

            series: [
                {
                    color:'rgb(191, 63, 63)',
                    name: charttype,
                    data: JSON.parse(data)
                }
            ]
        });
    }});
}
