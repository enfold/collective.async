/* The following line defines global variables defined elsewhere. */
/*globals require*/


if(require === undefined){
  require = function(reqs, torun){
    'use strict';
    return torun(window.jQuery);
  };
}

require([
  'jquery',
], function($) {
    'use strict';

    var data_div = $('#data');
    var timeout = 5000;
    var poll_url = data_div.attr('poll_url');
    var task_id = data_div.attr('task_id');

    function check_for_task_completion() {
        $.ajax({
            type: 'POST',
            url: poll_url,
            data: {
                task_id: task_id,
            },
            dataType: 'json',
            error: function(request, status, error) {
                setTimeout(check_for_task_completion, timeout);
            },
            success: function(data, status, request) {
                switch(data.status) {
                    case 'processing':
                        setTimeout(check_for_task_completion, timeout);
                        break;
                    case 'error':
                        $('#message').html(data.message)
                        break;
                    case 'success':
                        window.location.replace(data.redirect_url);
                        break;
                };
            },
        });
    }

    check_for_task_completion();
});