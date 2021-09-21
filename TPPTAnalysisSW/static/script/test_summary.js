$(document).ready(function() {
  var loadcount = 1 + $('#test_summaries').data('count');  // Session + tests

  function loadDone() {
    loadcount -= 1;
    if (loadcount == 0) {
      $('#print_button').prop('disabled', false);
    }
  }

  function sessionLoaded(data) {
    var dom = $(data);
    // Remove elements not belonging to the summary
    dom.find('.no_summary').remove();
    var content = dom.find('.content').html();
    $(this).html(dom.find('.content').html());

    $('.test_row').click(function() {
      window.location = '/tests/' + $(this).data('test-id');
    });

    loadDone();
  }

  function testLoaded(data) {
    var dom = $(data);

    // Add title
    var contents = dom.find('.test_title');
    contents.find('.no_summary').remove();
    $(this).append(contents);

    // Add the summary table
    var contents = dom.find('.test_verdicts');
    contents.find('.no_summary').remove();
    $(this).append(contents);

    loadDone();
  }

  function loadFailed() {
    alert('Report loading failed')
  }

  $('.test_sesession').each(function() {
    $.ajax({
       url: 'http://localhost:8081/testsessions/'.concat($(this).attr('id')),
       context: this,
     })
        .done(sessionLoaded)
        .fail(loadFailed);
  });

  $('.test_div').each(function() {
    $.ajax({
       url: 'http://localhost:8081/tests/' + $(this).attr('id') +
           '?noimages=true',
       context: this,
     })
        .done(testLoaded)
        .fail(loadFailed);
  });

  $('#print_button').click(function() {
    window.print();
  });
});