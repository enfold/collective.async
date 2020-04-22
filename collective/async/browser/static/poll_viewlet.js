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
  'underscore',
  'mockup-patterns-structure-url/js/views/generic-popover',
  'jquery.cookie'
], function($, _, GenericPopover) {
    'use strict';

    var inprogress_cookie_name = "async.tasks.inprogress",
        errored_cookie_name = "async.tasks.errors",
        poll_url = PORTAL_URL + '/@@check-for-tasks',
        task_detail_url = PORTAL_URL + '/@@task-details',
        timeout = 5000,
        initialized = false;

    function getTasksFromCookie(c_name) {
      var tasks = $.cookie(c_name);
      if (tasks !== undefined) {
        tasks = JSON.parse(tasks);
      } else {
        tasks = [];
      }
      return tasks;
    }

    function storeTasksInCookie(c_name, tasks) {
      $.cookie(c_name, JSON.stringify(tasks), { path: '/' });
      return;
    }

    function getIPTasksFromCookie() {
      var tasks = getTasksFromCookie(inprogress_cookie_name);
      return tasks;
    }

    function storeIPTasksInCookie(tasks) {
      storeTasksInCookie(inprogress_cookie_name, tasks);
      return;
    }

    function getErrorTasksFromCookie() {
      var tasks = getTasksFromCookie(errored_cookie_name);
      return tasks;
    }

    function storeErrorTasksInCookie(tasks) {
      storeTasksInCookie(errored_cookie_name, tasks);
      return;
    }

    function removeErrorTaskFromCookie(task_id) {
      var tasks = getErrorTasksFromCookie(),
          new_err_tasks = [];

      _.each(tasks, function(val) {
        if (val['task_id'] !== task_id){
          new_err_tasks.push(val);
        }
      });

      storeErrorTasksInCookie(new_err_tasks);
    }

    function addErrorTaskInCookie(task) {
      var tasks = getErrorTasksFromCookie(),
          new_err_tasks = [];

      _.each(tasks, function(val) {
        if (val['task_id'] !== task['task_id']){
          new_err_tasks.push(val);
        }
      });

      new_err_tasks.push(task);
      storeErrorTasksInCookie(new_err_tasks);
    }

    function renderAsyncMessage() {
      var tasks = getIPTasksFromCookie(),
          err_tasks = getErrorTasksFromCookie(),
          msg;
      if (tasks.length > 0){
        var msg_div = $("div#collective-async-polling div.alert-success div.message");
        msg_div.html("");
        var msg = $("<span></span>");
        if (tasks.length > 1){
          msg.html("There are "+ tasks.length +" background jobs running. ");
        } else {
          msg.html("There is "+ tasks.length +" background job running. ");
        }
        msg.append($("<a></a>")
                   .attr('href', task_detail_url)
                   .html("More details"))
        msg_div.append(msg);

        $("div#collective-async-polling div.alert-success").show();
      } else {
        $("div#collective-async-polling div.alert-success").hide();
      }

      _.each(err_tasks, function(val) {
        if ($("div#collective-async-polling div.alert-danger#"+val['task_id']).length > 0){
          // There's already an alert about this errored task, so ignore...
          return;
        }
        var err_alert = $("<div></div>")
                        .attr('id', val['task_id'])
                        .addClass("alert alert-danger");
        var err_msg = $("<div></div>")
                      .addClass("message")
                      .append($("<span></span>")
                              .html(val['error_message']))
                      .append($("<a></a>")
                              .attr('href', task_detail_url+'?task_id='+val['task_id'])
                              .html("Click here to learn more"))
                      .append($("<span></span>")
                              .addClass('close')
                              .html("X")
                              .on('click', function(){
                                removeErrorTaskFromCookie(val['task_id']);
                                err_alert.remove();
                              }));
        err_alert.append(err_msg);
        $("div#collective-async-polling").append(err_alert);
      });

    }

    function check_for_running_tasks() {
      console.log("Check running tasks");
      var tasks = getIPTasksFromCookie();
      console.log(tasks.length + " running tasks");
      if (tasks.length > 0){
        $.ajax({
            type: 'POST',
            url: poll_url,
            data: {
                task_ids: JSON.stringify(tasks),
                current_location: JSON.stringify(window.location),
            },
            dataType: 'json',
            error: function(request, status, error) {
                setTimeout(check_for_running_tasks, timeout);
            },
            success: function(data, status, request) {
                var patternStructure = $("div.pat-structure").data('patternStructure'),
                    ip_tasks = [];

                // First, store tasks that are "in process" in cookie
                _.each(data['processing'], function(val) {
                  if (val['task_id'] !== undefined){
                    ip_tasks.push(val['task_id']);
                  }
                });
                storeIPTasksInCookie(ip_tasks);

                if(data['processing'].length == 0){
                  if (patternStructure !== undefined){
                    // If there are no tasks in progress, then clear the
                    // status from the folder_contents view (if any)
                    patternStructure.view.setStatus();
                  }
                }
                if(data['success'].length > 0){
                  if (patternStructure !== undefined){
                    // If there are tasks that succeded, then refresh the
                    // folder_contents table (If currently at the
                    // folder_contents)
                    patternStructure.view.collection.pager();
                  }
                }
                _.each(data['error'], function(val) {
                  if (val['task_id'] !== undefined){
                    // Add tasks that errored to a separate cookie
                    addErrorTaskInCookie(val);
                  }
                });

                setTimeout(check_for_running_tasks, timeout);
                renderAsyncMessage();

                if (data['should_reload'] !== undefined &&
                    data['should_reload'] == true){
                  window.location.reload();
                }
            },
        });
      }
    }

    function afterClickButton(data){
      // Add task to the list in cookie
      var task_id = data['task_id'];
      if (task_id != undefined) {
        var tasks = getIPTasksFromCookie();
        tasks.push(task_id);
        storeIPTasksInCookie(tasks);
      }
      check_for_running_tasks();
    }

    function buttonClickEvent() {
      var self = this;
      self.buttonClickEvent.call(self, arguments[0], arguments[1], afterClickButton);
    }

    var CallbackPopoverView = GenericPopover.extend({
          applyButtonClicked: function() {
            var self = this;
            var data = {};
            _.each(self.$el.find('form').serializeArray(), function(param) {
              if (param.name in data) {
                  data[param.name] += ',' + param.value;
              } else {
                  data[param.name] = param.value;
              }
            });
            self.app.buttonClickEvent(this.triggerView, data, afterClickButton);
            self.hide();
          },
    });

    $(document).ready(function() {
      check_for_running_tasks();
      renderAsyncMessage();

      $('body').on('context-info-loaded', function(){
        if (!initialized) {
          // If we have the structure pattern here, we will remove the event bound
          // to some buttons and re-bind them to include a callback
          var struc_pattern = $("div.pat-structure").data('patternStructure');
          if (struc_pattern !== undefined){
            var app = $("div.pat-structure").data('patternStructure').view
            _.each(app.buttons.items, function(button) {
              var rebind = false;
              try {
                if (button.id == 'delete'){
                  rebind = true;
                }
                if (button.id == 'paste'){
                  rebind = true;
                }
                if (rebind) {
                  if (button.form) {
                    var form_view = button.options.triggerView._events['button:click'][0];
                    var new_view = new CallbackPopoverView(button.options);
                    var old_el = app.$el.find('#'+new_view.el.id);
                    $(old_el).remove();
                    form_view.context = new_view;
                    app.$el.append(new_view.el);
                  } else {
                    button.off('button:click');
                    button.on('button:click', buttonClickEvent, app);
                  }
                }
              } catch (err) {
                console.error('Error with button "' + button.id + '": ' + err);
              }
            });
          }
        }
        initialized = true;
      })
    });

//$("div.pat-structure").data('patternStructure').view.collection.pager()
});
