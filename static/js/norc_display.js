
// TODO: Fix double-clicking sometimes opening two details tables.
// TODO: Make pagination not query every page change?
// TODO: Sorting (sorttables?)
// TODO: Log viewing.
// TODO: Daemon interactive control.
// TODO: Job/Iteration views.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation


var DAEMON_DETAILS_ON = {}

// ATTN: The names of these headers are unTitle'd and then used directly
//       to pull data from JSON objects; changing them here requires a
//       change on the backend as well.
var DAEMON_DETAIL_HEADERS = [
    'Task ID', 'Job', 'Task', 'Status', 'Started', 'Ended'
];
var DAEMON_HEADERS = [
    'ID', 'Type', 'Region', 'Host', 'PID', 'Running', 'Success',
    'Errored', 'Status', 'Started', 'Ended'
];
var SINCE = 'all';

var nextPage = 0, prevPage = 0;

// Takes a string like 'abc_xyz' and converts it to 'Abc Xyz'.
function toTitle(str) {
    return str.split('_').map(function(word) {
        return String.concat(word.charAt(0).toUpperCase(), word.substr(1));
    }).join(' ');
}

// Takes a string like 'Abc Xyz' and converts it to 'abc_xyz'.
function unTitle(str) {
    return str.split(' ').map(function(word){
        return word.toLowerCase();
    }).join('_');
}

// Constructs a table out of the AJAX response for daemon details.
function makeDetailsTable(data) {
    var table = $('<table class="details"></table>');
    var header_row = $('<tr/>');
    $.each(DAEMON_DETAIL_HEADERS, function(i, header) {
        header_row.append($('<th/>').append(header));
    });
    table.append(header_row);
    $.each(data, function(task_id, trs_data) {
        var row = $('<tr/>');
        row.addClass(trs_data['status'].toLowerCase());
        // Add the ID cell.
        row.append($('<td></td>').append(task_id));
        headers = DAEMON_DETAIL_HEADERS.map(unTitle).slice(1);
        $.each(headers, function(i, head) {
            row.append($('<td></td>').append(trs_data[head]));
        });
        table.append(row);
    });
    return table;
}

// Inserts a new row after rowAbove with the given ID and contents using
// the jQuery slideDown animation.
function insertNewRow(rowAbove, newID, contents, animation) {
    var row = $('<tr><td><div></div></td></tr>').attr('id', newID);
    row.find('td').attr('colspan', rowAbove.find('td').length)
        .find('div').css('display', 'none').append(contents);
    rowAbove.after(row);
    if (!animation) {
        animation = function(d) {
            d.slideDown(300);
        };
    }
    animation($('#' + newID + ' div:first'));
}

function toggleDetails(id) {
    var row = $('#ndss #' + id + 'details');
    if (row.length > 0) {
        hideDetails(id);
    } else {    
        showDetails(id);
    }
}

function showDetails(id, animation) {
    DAEMON_DETAILS_ON[id] = true;
    $.get('/daemons/' + id + '/', function(data) {
        if (!$.isEmptyObject(data)) {
            // table.addClass('details');
            insertNewRow(
                $('#ndss #' + id),
                id + 'details',
                makeDetailsTable(data),
                animation
            );
        }
    });
}

function hideDetails(id) {
    DAEMON_DETAILS_ON[id] = false;
    row = $('#ndss #' + id + 'details');
    row.find('div').slideUp(300, function() {
        row.detach();
    });
}

function makeDaemonTable(data) {
    $.each(data.daemons, function(daemon_id, nds) {
        if ($('#ndss #' + daemon_id).length > 0) {
            $('#ndss #' + daemon_id).remove();
        }
        var row = $('<tr></tr>', {
            id : daemon_id,
            onclick : 'toggleDetails(' + daemon_id + ')',
        });
        row.append($('<td></td>').append(daemon_id));
        headers = DAEMON_HEADERS.map(unTitle).slice(1);
        $.each(headers, function(i, head) {
            row.append($('<td></td>').append(nds[head]));
        });
        $('#ndss table:first').append(row);
        if (DAEMON_DETAILS_ON[daemon_id]) {
            showDetails(daemon_id, function(d) {
                d.css('display', 'block');
            });
        }
    });
    $('#ndss tbody > tr:even').addClass('even');
    $('#ndss tbody > tr:odd').addClass('odd');
    // debugger;
    if (data.page.next != 0) {
        $('#ndss .next_page').css('display', 'inline');
        nextPage = data.page.next;
    } else {
        $('#ndss .next_page').css('display', 'none');
    }
    if (data.page.prev != 0) {
        $('#ndss .prev_page').css('display', 'inline');
        prevPage = data.page.prev;
    } else {
        $('#ndss .prev_page').css('display', 'none');
    }
}

function updateDaemons(filters) {
    if (!filters) filters = {};
    if ('since' in filters) {
        SINCE = filters.since;
    } else {
        filters.since = SINCE;
    }
    $.get('/daemons/', filters, function(data) {
        $('#ndss tr:has(td)').remove();
        makeDaemonTable(data);
    });
}
$(document).ready(function() {
    updateDaemons();
    $('#ndss .next_page').click(function() {
        updateDaemons({page : nextPage});
    });
    $('#ndss .prev_page').click(function() {
        updateDaemons({page : prevPage});
    });
    $('#timeframe span').addClass('clickable');
    $('#page_nav span').addClass('clickable');
});
