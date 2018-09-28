
//saltstack命令执行使用的参数
    	var argcount=2;
    	var kwargcount=2;
    	$(function(){
//不知道为什么放在function外面的话竟然影响我的页面所以放里头，引用toastr全局下添加这个是显示位子在中上位子toast-center-center是在toastr.min.js中自己增加的
    		toastr.options.positionClass = 'toast-center-center';


	        // 点击添加一个saltstack命令的arg输入框
	        $("#add_arg").click(function(){
	        	var add_arg='<input type="text" class="form-control input-control" id="arg'+argcount+'" placeholder="arg'+argcount+'"  style="width: 120px;font-size: 14px;" >';
	        	$("#add1").before(add_arg);
	        	argcount++;
	        });

	        // 点击添加一个saltstack命令的kwarg输入框
	        $("#add_kwarg").click(function(){
	        	var add_kwarg='<input type="text" class="form-control input-control" id="kwarg'+kwargcount+'" placeholder="kwarg'+kwargcount+'"  style="width: 120px;font-size: 14px;" >';
	        	$("#add2").before(add_kwarg);
	        	kwargcount++;
	        });


			

             



    	});

    	// 模态框居中
    	function centerModals() {
		    $('.juzhong').each(function(i) {
		        var $clone = $(this).clone().css('display', 'block').appendTo('body'); var top = Math.round(($clone.height() - $clone.find('.modal-content').height()) / 4);
		        top = top > 0 ? top : 0;
		        $clone.remove();
		        $(this).find('.modal-content').css("margin-top", top);
		    });
		}
		$('.juzhong').on('show.bs.modal', centerModals);
		$(window).on('resize', centerModals);
		// 模态框拖拽功能未实现
