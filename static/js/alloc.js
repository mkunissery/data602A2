var resizefunc = [];
var $ = jQuery;
var jSellValue = 0
$(document).ready(function(){

    // By Default

    //Positions
    $.ajax({url: "http://127.0.0.1:5000/Allocation", success: function(result){
        var data = result.replace(/&lt;/g,"<").replace(/&gt;/g,">")
        $("#Allocation").html(data);
      
    }});

});
   