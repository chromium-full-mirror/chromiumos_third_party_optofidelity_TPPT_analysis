/**
 * Enum of possible states a test can be in. Should match the equivalent Enum
 * defined in spec_validators.py
 * @enum {string}
 */
const TestStatus = {
  kPass: 'Pass',
  kBorderline: 'Borderline',
  kFail: 'Fail',
};

$(document).ready(function() {
  $('.pass_select').each(function() {
    if ($(this).hasClass('select_initially_passed')) {
      $(this).val(TestStatus.kPass)
      $(this).addClass(TestStatus.kPass)
      $(this).removeClass(TestStatus.kFail)
    } else {
      $(this).val(TestStatus.kFail)
      $(this).addClass(TestStatus.kFail)
      $(this).removeClass(TestStatus.kPass)
    }
  });

  $('.pass_select').change(function() {
    if ($('option:selected', this).hasClass(TestStatus.kPass)) {
      $(this).addClass(TestStatus.kPass)
      $(this).removeClass(TestStatus.kFail)
    } else {
      $(this).addClass(TestStatus.kFail)
      $(this).removeClass(TestStatus.kPass)
    }
  });

  $('#print_button').click(function() {
    window.print();
  });


  $('#upload_button').click(function() {
    $.post(window.location.href.split('?')[0] + '/upload', function(data) {
      alert(JSON.stringify(data));
      window.location.reload();
    });
  });
});
