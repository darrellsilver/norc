
// TODO: Fix double-clicking sometimes opening two details tables.
// TODO: Make pagination not query every page change?
// TODO: Sorting (sorttables?)
// TODO: Log viewing.
// TODO: Daemon interactive control.
// TODO: Job/Iteration views.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation


/****************
    Constants
****************/

// ATTN: The names of these headers are unTitle'd and then used directly
//       to pull data from JSON objects; changing them here requires a
//       change on the backend as well or stuff will break.
var DAEMON_DETAIL_HEADERS = [
    'Task ID', 'Job', 'Task', 'Status', 'Started', 'Ended'
];
var DAEMON_HEADERS = [
    'ID', 'Type', 'Region', 'Host', 'PID', 'Running', 'Success',
    'Errored', 'Status', 'Started', 'Ended'
];
var STATUS_CLASSES = {
    SUCCESS : 'status_good',
    RUNNING : 'status_good',
    CONTINUE : 'status_warning',
    RETRY : 'status_warning',
    SKIPPED : 'status_warning',
    TIMEDOUT : 'status_error',
    ERROR : 'status_error',
};
var BORDER_DARK = '1px solid #000';
var BORDER_LIGHT = '1px solid #AAA';

// Saved state of the page.
var state = {
    // Whether details were showing for each daemon.
    daemonDetailsShowing : {},
    // The last 'since' selection.
    since : 'all',
    // What the next and previous page numbers are.
    nextPage : 0, prevPage : 0,
}


/****************
    Utilities
****************/

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

// Creates a table.
function makeTable(headers, data, idSetup, colorStatus) {
    var table = $('<table/>').append($('<tr/>'));
    $.each(headers, function(i, h) {
        table.find('tr').append($('<th/>').append(h));
    });
    $.each(data, function(id, rowData) {
        // Make the row and add the ID cell.
        var row = $('<tr/>').append($('<td/>').append(id));
        if (idSetup) row.attr('id', idSetup[0] + id + idSetup[1]);
        if (colorStatus && 'status' in rowData) {
            row.addClass(STATUS_CLASSES[rowData['status']]);
        }
        $.each(headers.map(unTitle).slice(1), function(i, h) {
            row.append($('<td/>').append(rowData[h]));
        });
        table.append(row);
    });
    return table;
}

// DEPR
// Constructs a table out of the AJAX response for daemon details.
function makeDetailsTable(data) {
    var table = $('<table/>').addClass('details');
    var header_row = $('<tr/>');
    $.each(DAEMON_DETAIL_HEADERS, function(i, header) {
        header_row.append($('<th/>').append(header));
    });
    table.append(header_row);
    $.each(data, function(task_id, trs_data) {
        var row = $('<tr/>');
        row.addClass(STATUS_CLASSES[trs_data['status']]);
        // Add the ID cell.
        row.append($('<td/>').append(task_id));
        headers = DAEMON_DETAIL_HEADERS.map(unTitle).slice(1);
        $.each(headers, function(i, head) {
            // var cell = $('<td/>').append(trs_data[head]);
            // if (head == 'status') {
            //     cell.addClass(STATUS_CLASSES[trs_data['status']]);
            // }
            row.append($('<td/>').append(trs_data[head]));
        });
        table.append(row);
    });
    return table;
}

// Inserts a new row after rowAbove with the given ID and
// contents using the given animation (defaults to slideDown).
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

function styleExpandRow(row) {
    row.children('td:first').css('borderLeft', BORDER_DARK);
    row.children('td:last').css('borderRight', BORDER_DARK);
    row.children('td').css('borderTop', BORDER_DARK);
    row.addClass('expanded_row');
}

function styleCollapseRow(row) {
    row.children('td:first').css('borderLeft', BORDER_LIGHT);
    row.children('td:last').css('borderRight', BORDER_LIGHT);
    row.children('td').css('borderTop', '');
    row.removeClass('expanded_row');
}
/*********************
    Core Functions
*********************/

function toggleDetails(id) {
    if ($('#ndss #' + id + 'details').length > 0) {
        hideDetails(id);
    } else {    
        showDetails(id);
    }
}

function showDetails(id, animation) {
    state.daemonDetailsShowing[id] = true;
    $.get('/daemons/' + id + '/', function(data) {
        var content;
        if (!$.isEmptyObject(data)) {
            content = makeTable(DAEMON_DETAIL_HEADERS, data, [], true);
        } else {
            content = $('<div/>', {text : 'No tasks.','class' : 'no_tasks'});
        }
        content.addClass('details');
        var row = $('#ndss #' + id);
        insertNewRow(row, id + 'details', content, animation);
        $('#ndss #' + id + 'details').addClass('data_row');
        styleExpandRow(row);
    });
}

function hideDetails(id) {
    state.daemonDetailsShowing[id] = false;
    row = $('#ndss #' + id + 'details');
    row.find('div').slideUp(300, function() {
        row.detach();
        styleCollapseRow($('#ndss #' + id));
    });
}

// DEPR
function makeDaemonTable(data) {
    
    $.each(data.daemons, function(daemon_id, nds) {
        if ($('#ndss #' + daemon_id).length > 0) {
            $('#ndss #' + daemon_id).remove();
        }
        var row = $('<tr/>', {
            id : daemon_id,
            onclick : 'toggleDetails(' + daemon_id + ')',
        });
        row.append($('<td/>').append(daemon_id));
        headers = DAEMON_HEADERS.map(unTitle).slice(1);
        $.each(headers, function(i, head) {
            row.append($('<td/>').append(nds[head]));
        });
        $('#ndss table:first').append(row);
        if (state.daemonDetailsShowing[daemon_id]) {
            showDetails(daemon_id, function(d) {
                d.css('display', 'block');
            });
        }
    });
    $('#ndss tbody > tr:even').addClass('even');
    $('#ndss tbody > tr:odd').addClass('odd');
    $('#ndss tbody > tr').hover(function() {
        $(this).toggleClass('tr_hover');
    });
    if (data.page.next != 0) {
        $('#ndss .next_page').css('display', 'inline');
        state.nextPage = data.page.next;
    } else {
        $('#ndss .next_page').css('display', 'none');
    }
    if (data.page.prev != 0) {
        $('#ndss .prev_page').css('display', 'inline');
        state.prevPage = data.page.prev;
    } else {
        $('#ndss .prev_page').css('display', 'none');
    }
}

function setupDaemonSection(data) {
    table = makeTable(DAEMON_HEADERS, data.daemons, ['', '']);
    // table.addClass('data_table');
    $('#ndss > table').replaceWith(table);
    table = table.children('tbody');
    table.children('tr').each(function(i) {
        row = $(this);
        // row.addClass('data_row');
        if (i == 0) {
            row.children('th:first').css('borderLeft', BORDER_LIGHT);
            row.children('th:last').css('borderRight', BORDER_LIGHT);
        } else {
            row.children('td:first').css('borderLeft', BORDER_LIGHT);
            row.children('td:last').css('borderRight', BORDER_LIGHT);
            row.hover(function() {
                $(this).toggleClass('tr_hover');
            });
        }
        var id = row.attr('id');
        row.click(function() {
            toggleDetails(id);
        });
        if (state.daemonDetailsShowing[id]) {
            showDetails(id, function(d) {
                d.css('display', 'block');
            });
        }
    });
    table.children('tr:even').addClass('even');
    table.children('tr:odd').addClass('odd');
    if (data.page.next != 0) {
        $('#ndss .next_page').css('display', 'inline');
        state.nextPage = data.page.next;
    } else {
        $('#ndss .next_page').css('display', 'none');
    }
    if (data.page.prev != 0) {
        $('#ndss .prev_page').css('display', 'inline');
        state.prevPage = data.page.prev;
    } else {
        $('#ndss .prev_page').css('display', 'none');
    }
}

function refreshDaemonSection(filters) {
    if (!filters) filters = {};
    if ('since' in filters) {
        state.since = filters.since;
    } else {
        filters.since = state.since;
    }
    $.get('/daemons/', filters, function(data) {
        setupDaemonSection(data);
    });
}

$(document).ready(function() {
    refreshDaemonSection();
    $('#ndss .next_page').click(function() {
        refreshDaemonSection({page : state.nextPage});
    });
    $('#ndss .prev_page').click(function() {
        refreshDaemonSection({page : state.prevPage});
    });
    $('#timeframe span').addClass('clickable');
    $('#page_nav span').addClass('clickable');
});
