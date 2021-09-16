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
], function($, _, GenericPopover) {
    'use strict';

    var poll_url = PORTAL_URL + '/@@check-for-tasks',
        task_detail_url = PORTAL_URL + '/@@task-details',
        mark_task_seen = PORTAL_URL + '/@@task-seen',
        timeout = 5000,
        initialized = false;

    function getIPTasks() {
      var tasks = [];
      var selector = 'div#collective-async-polling div#async-inprogress-tasks span';
      var spans = $(selector).toArray();
      _.each(spans, function (span){
          tasks.push(span.textContent);
      });

      var ip_tasks = $("div#collective-async-polling").data('ip_tasks');
      if (ip_tasks === undefined){
          ip_tasks = [];
      }
      _.each(ip_tasks, function (task){
          tasks.push(task);
      });

      return tasks;
    }

    function removeIPTask(task_id) {
      var tasks = [];
      var selector = 'div#collective-async-polling div#async-inprogress-tasks span';
      var spans = $(selector).toArray();
      _.each(spans, function (span){
          if (span.textContent === task_id){
              $(span).remove();
          }
      });

      var ip_tasks = $("div#collective-async-polling").data('ip_tasks');
      if (ip_tasks === undefined){
          ip_tasks = [];
      }
      const index = ip_tasks.indexOf(task_id);
      if (index > -1) {
        ip_tasks.splice(index, 1);
      }

      $("div#collective-async-polling").data('ip_tasks', ip_tasks);
    }

    function getErrorTasks() {
      var tasks = [];
      var selector = 'div#collective-async-polling div#async-error-tasks span';
      var spans = $(selector).toArray();
      _.each(spans, function (span){
          tasks.push(span.textContent);
      });
      return tasks;
    }

    function renderAsyncMessage(ip_tasks, err_tasks) {
      var msg;
      if (ip_tasks.length > 0){
        var msg_div = $("div#collective-async-polling div.alert-success div.message");
        msg_div.html("");
        var msg = $("<span></span>");
        if (ip_tasks.length > 1){
          msg.html("There are "+ ip_tasks.length +" background jobs running. ");
        } else {
          msg.html("There is "+ ip_tasks.length +" background job running. ");
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
        var seen = false;
        _.each(getTasksSeen(), function(task_id) {
            if (task_id == val['task_id']){
                seen = true;
            }
        })
        if (seen){
            return;
        }

        var err_alert = $("<div></div>")
                        .attr('id', val['task_id'])
                        .addClass("alert alert-danger portalMessage");
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
                                markTaskSeen(val['task_id']);
                                err_alert.remove();
                              }));
        err_alert.append(err_msg);
        $("div#collective-async-polling").append(err_alert);
      });

    }

    function addTaskIP(task_id) {
        var ip_tasks = $("div#collective-async-polling").data('ip_tasks');
        if (ip_tasks === undefined){
            ip_tasks = [];
        }
        ip_tasks.push(task_id);
        $("div#collective-async-polling").data('ip_tasks', ip_tasks);
    }

    function addTaskSeen(task_id) {
        var seen_tasks = $("div#collective-async-polling").data('seen_tasks');
        if (seen_tasks === undefined){
            seen_tasks = [];
        }
        seen_tasks.push(task_id);
        $("div#collective-async-polling").data('seen_tasks', seen_tasks);
    }

    function getTasksSeen() {
        var seen_tasks = $("div#collective-async-polling").data('seen_tasks');
        if (seen_tasks === undefined){
            seen_tasks = [];
        }
        return seen_tasks;
    }

    function markTaskSeen(task_id) {
      $.ajax({
          type: 'POST',
          url: mark_task_seen,
          data: {
              task_id: task_id
          },
          dataType: 'json',
          success: function(data, status, request) {
              addTaskSeen(task_id);
          },
      });

    }

    function check_for_running_tasks() {
      console.log("Check running tasks");
      var ip_tasks = getIPTasks();
      $.ajax({
          type: 'POST',
          url: poll_url,
          data: {
              ip_task_ids: JSON.stringify(ip_tasks),
              current_location: JSON.stringify(window.location)
          },
          dataType: 'json',
          error: function(request, status, error) {
              setTimeout(check_for_running_tasks, timeout);
          },
          success: function(data, status, request) {
              var patternStructure = $("div.pat-structure").data('patternStructure'),
                  ip_tasks = [],
                  err_tasks = [];

              _.each(data['processing'], function(val) {
                  if (val['task_id'] !== undefined){
                  ip_tasks.push(val);
                  }
              });

              _.each(data['error'], function(val) {
                  if (val['task_id'] !== undefined){
                  err_tasks.push(val);
                  }
              });

              if(data['processing'].length == 0){
                  if (patternStructure !== undefined){
                  // If there are no tasks in progress, then clear the
                  // status from the folder_contents view (if any)
                  patternStructure.view.clearStatus();
                  }
              }
              if(data['success'].length > 0){
                  if (patternStructure !== undefined){
                  // If there are tasks that succeded, then refresh the
                  // folder_contents table (If currently at the
                  // folder_contents)

                  _.each(data['success'], function(val) {
                    if (val['task_id'] !== undefined){
                      removeIPTask(val['task_id']);
                    }
                  });
                  patternStructure.view.collection.pager();
                  }
              }

              setTimeout(check_for_running_tasks, timeout);
              renderAsyncMessage(ip_tasks, err_tasks);

              if (data['should_reload'] !== undefined &&
                  data['should_reload'] == true){
                window.location.reload();
              }
          },
      });

    }
    function afterClickButton(data){
      var task_id = data['task_id'];
      addTaskIP(task_id);
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
    });
    $(window).load(function() {
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
                if (button.id == 'rename'){
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
    });

//$("div.pat-structure").data('patternStructure').view.collection.pager()
});
