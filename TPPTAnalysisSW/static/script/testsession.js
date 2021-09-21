$(document).ready(function() {
  function notesSaved(data) {
    // alert(data);
    $('#notes').html(data);
    $('#notes').show();
    $('#notes_editor').hide();
    $('#notes_edit').show();
    $('#notes_save').hide();
  }

  function notesError() {
    alert('Saving of notes failed');
  }

  $('.test_row').click(function() {
    window.location = '/tests/' + $(this).data('test-id');
  });

  $('.upload_test_button').click(function() {
    var location = window.location.href.split('?')[0] +
        '/upload_test?test_id=' + $(this).data('test-id');

    $.post(location, function(data) {
      alert(JSON.stringify(data));
      // Reload to refresh the disabled status for all the buttons on the page
      window.location.reload();
    });
  });

  $('#upload_session_button').click(function() {
    var location = window.location.href.split('?')[0] +
        '/upload_session?session_id=' + $(this).data('session-id');

    $.post(location, function(data) {
      alert(JSON.stringify(data));
      // Reload to refresh the disabled status for all the buttons on the page
      window.location.reload();
    });
  });

  $('#notes_save').click(function() {
    var data = {command: 'set_notes', value: $('#notes_editor').val()};
    $.ajax({type: 'POST', data: {data: JSON.stringify(data)}, datatype: 'text'})
        .done(notesSaved)
        .fail(notesError);
  });

  $('#notes_edit').click(function() {
    $('#notes').hide();
    $('#notes_editor').show();
    $('#notes_edit').hide();
    $('#notes_save').show();
  });
});
