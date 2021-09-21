$(document).ready(function() {
  //
  // Main page status related functions
  //

  var loadstate = function() {
    if (typeof (Storage) !== 'undefined') {
      if (sessionStorage.view) {
        if (sessionStorage.view == 'latest') {
          select_latest()
        } else if (sessionStorage.view == 'manufacturers') {
          select_manufacturers()
        }
      } else {
        select_latest()
      }
      if (sessionStorage.manufacturers) {
        var mselections = JSON.parse(sessionStorage.manufacturers)
        if ($.isArray(mselections)) {
          show_manufacturers(mselections);
        }
      }
    }
  };

  var show_manufacturers = function(mselections) {
    // This breaks if the tree is changed while browsing -> currently "too bad"
    $('.collapsing-header').each(function() {
      if ($.inArray($(this).data('indx'), mselections) != -1) {
        togglerow.call(this)
      }
    });
  };

  var saveview = function(currentview) {
    if (typeof (Storage) !== 'undefined') {
      sessionStorage.view = currentview;
    }
  };

  // Save individual manufacturer row (indx) state (true=visible, false=hidden)
  var savemselection = function(indx, state) {
    if (typeof (Storage) !== 'undefined') {
      if (sessionStorage.manufacturers) {
        var mselections = JSON.parse(sessionStorage.manufacturers);
      } else {
        var mselections = [];
      }
      if (state) {
        mselections.push(indx);
      } else {
        var index = $.inArray($(this).data('indx'), mselections);
        if (index != -1) {
          mselections.splice(index, 1);
        }
      }

      sessionStorage.manufacturers = JSON.stringify(mselections);
    }
  };

  //
  // Navigation
  //

  var select_latest =
      function() {
    $('#view_latest').show();
    $('#view_manufacturers').hide();
    $('.viewselector').removeClass('selected');
    $('#viewsel_latest').addClass('selected');
    saveview('latest');
  }

  var select_manufacturers =
      function() {
    $('#view_latest').hide();
    $('#view_manufacturers').show();
    $('.viewselector').removeClass('selected');
    $('#viewsel_manufacturers').addClass('selected');
    saveview('manufacturers');
  }

      $('#viewsel_latest')
          .click(select_latest);

  $('#viewsel_manufacturers').click(select_manufacturers);

  var togglerow = function() {
    if (!$(this).data('shown')) {
      // Save the table-row display style to jquery memory...
      $(this).siblings().css('display', 'table-row');
      $(this).siblings().toggle();
      $(this).data('shown', 'true');
    }
    $(this).siblings().toggle('fast');
    $(this).children('.collapsing-icon').children().toggle();  // Change + -> -
  };

  $('.collapsing-header').click(function() {
    togglerow.call(this);

    if ($(this).css('display') == 'none') {
      savemselection($(this).data('indx'), false);
    } else {
      savemselection($(this).data('indx'), true);
    }
  });

  //
  // Test session navigation
  //

  $('.test_session_row td:not(:last-child)').click(function(e) {
    if ($(this).hasClass('ban')) {
      e.stopPropagation();
    } else {
      window.location = 'testsessions/' + $(this).parent().data('id');
    }
  });

  $(function() {
    $('#deleteRequest').click(function() {
      $('#deletemodal').modal('hide');
      $.ajax({
         type: 'POST',
         url: '/',
         async: false,
         data: {params: 'delete', id: $(this).data('id')},
       })
          .done(location.reload(true))
          .fail(deletefail);
    });
  });

  $('#deletemodal').on('show.bs.modal', function(event) {
    var cell = $(event.relatedTarget);
    var sessionId = cell.data('id');
    var modal = $(this);
    modal.find('.idspan').text(sessionId);
    var button = modal.find('#deleteRequest');
    button.data('id', sessionId);
  });

  //
  // Recalculate all
  //

  var progress;

  var postsuccess = function(data) {
    progress.close();
    $('#Main').show();
    $('#loading').hide();
    location.reload(true);
  };

  var postfail = function(data) {
    progress.close();
    alert('Recalculation failed: server error');
    $('#Main').show();
    $('#loading').hide();
  };

  var deletefail = function(data) {
    alert('Deletion failed: server error');
    $('#Main').show();
    $('#loading').hide();
  };

  $('#recalculate_button').click(function() {
    $('#Main').hide();
    $('#loading').show();

    progress = new EventSource('?event=progress');

    progress.onmessage = function(event) {
      var val = Math.round(event.data * 100);
      if (val <= 99) {
        $('.prog').text(val);
        $('.progress-bar').css('width', val + '%').attr('aria-valuenow', val);
      } else {
        $('.prog').text(100);
        $('.progress-bar').css('width', 100 + '%').attr('aria-valuenow', 100);
      }
    };

    $.ajax({
       type: 'POST',
       url: '/',
       data: {params: 'recalculate'},
     })
        .done(postsuccess)
        .fail(postfail);
  });

  //
  // Initializations
  //

  $('.notes').each(function() {
    text = $(this).text();
    if (text.length > 20)
      $(this).text(text.substr(0, 20));
  });

  loadstate();
});
