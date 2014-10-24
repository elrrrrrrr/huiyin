var $ = require('jquery');

$(".piece").each(function(i,e){
        var el = $(e),
            id = el.attr("data-id"),
            del = el.find(".del"),
            delay;

        if(!id){
            el.click(function(){return false;})
            return;
        }

        if($(window).width() > 480 ){ 
        el.on("mouseenter",function(){
            clearTimeout(delay);
            delay = setTimeout(function(){
                del.animate({
                    right:-20
                },{
                    duration:200
                });
            },200);
        })
        .on("mouseleave",function(){
            clearTimeout(delay);
            delay = setTimeout(function(){
                del.animate({
                    right:0
                },{
                    duration:200
                });
            },300);
        });
        }

        del.on("click",function(){
            if(!confirm("确认删除？")){return}

            $.ajax({
                url:"/ajax/delete/" + id
            }).success(function(json){
                el.css("overflow","hidden");
                el.animate({
                    height:0,
                    opacity:0
                },{
                    duration:625,
                    complete:function(){
                        el.remove();
                    }
                });
            });
        });
    });