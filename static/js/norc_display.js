
// TODO: Fix double-clicking sometimes opening two details tables.
// TODO: Sorting (sorttables?)
// TODO: Log viewing.
// TODO: Daemon interactive control.
// TODO: Job/Iteration views.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation
// TODO: Comment this file. (javadoc style?)


/****************
    Constants
****************/

// ATTN: The names of these headers are unTitle'd and then used directly
//       to pull data from JSON objects; changing them here requires a
//       change on the backend as well or stuff will break.
var HEADERS = {
    'daemons': ['ID', 'Type', 'Region', 'Host', 'PID', 'Running',
        'Success', 'Errored', 'Started', 'Ended', 'Status'],
    'jobs': ['ID', 'Name', 'Description', 'Added'],
};
var DETAIL_HEADERS = {
    'daemons': ['Task ID', 'Job', 'Task', 'Started', 'Ended', 'Status'],
    'jobs': ['Status', 'Type', 'Started', 'Ended'],
};

var STATUS_CLASSES = {
    SUCCESS : 'status_good',
    RUNNING : 'status_good',
    CONTINUE : 'status_warning',
    RETRY : 'status_warning',
    SKIPPED : 'status_warning',
    TIMEDOUT : 'status_error',
    ERROR : 'status_error',
    ENDED : 'status_good',
    DELETED : 'status_error',
};
var BORDER_DARK = '1px solid #000';

// Saved state of the page.
var state = {
    'daemons' : {
        // Whether details were showing for each daemon.
        detailsShowing : {},
        // The last 'since' selection.
        since : 'all',
        // What the next and previous page numbers are.
        nextPage : 0, prevPage : 0,
    },
    'jobs': {
        // Whether details were showing for each daemon.
        detailsShowing : {},
        // The last 'since' selection.
        since : 'all',
        // What the next and previous page numbers are.
        nextPage : 0, prevPage : 0,
    }
}


/****************
    Utilities
****************/

/**
 * Takes a string like 'abc_xyz' and converts it to 'Abc Xyz'.
 *
 * @param str   A string to format.
 * @return      The formatted string.
 */
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
    // if (colorStatus == undefined) colorStatus = true;
    var table = $('<table/>');
    var hrow = $('<tr/>');
    $.each(headers, function(i, h) {
        hrow.append($('<th/>').append(h));
    });
    table.append(hrow);
    $.each(data, function(id, rowData) {
        // Make the row and add the ID cell.
        var row = $('<tr/>').append($('<td/>').append(id));
        if (idSetup) row.attr('id', idSetup[0] + id + idSetup[1]);
        $.each(headers.map(unTitle).slice(1), function(i, h) {
            var cell = $('<td/>').append(rowData[h]);
            if (colorStatus && h == 'status') {
                cell.addClass(STATUS_CLASSES[rowData['status']]);
            }
            row.append(cell);
        });
        table.append(row);
    });
    table.children('tbody').children('tr:even').addClass('even');
    table.children('tbody').children('tr:odd').addClass('odd');
    return table;
}

function initDataTable(section, table) {
    table = table.children('tbody');
    table.find('th:first').addClass('leftEdge');
    table.find('th:last').addClass('rightEdge');
    table.children('tr:has(td)').each(function(i, row) {
        row = $(row);
        row.children('td:first').addClass('leftEdge');
        row.children('td:last').addClass('rightEdge');
        row.hover(function() {
            $(this).addClass('hover');
        }, function() {
            $(this).removeClass('hover');
        });
        var id = row.children('td:first').text();
        row.click(function() {
            toggleDetails(section, id);
        });
        if (state[section].detailsShowing[id]) {
            showDetails(section, id, function(d) {
                d.css('display', 'block');
            });
        }
    });
}

// Inserts a new row after rowAbove with the given ID and
// contents using the given animation (defaults to slideDown).
function insertNewRow(rowAbove, contents, animation) {
    // debugger;
    var row = $('<tr><td><div></div></td></tr>');
    row.find('td').attr('colspan', rowAbove.children('td').length)
        .find('div').css('display', 'none').append(contents);
    rowAbove.after(row);
    if (!animation) {
        animation = function(d) {
            d.slideDown(300);
        };
    }
    animation(row.find('div:first'));
    return row;
}

/*********************
    Core Functions
*********************/

function toggleDetails(section, id) {
    if ($('#' + section + id + 'details').length > 0) {
        hideDetails(section, id);
    } else {    
        showDetails(section, id);
    }
}

function showDetails(section, id, animation) {
    state[section].detailsShowing[id] = true;
    $.get('/data/' + section + '/' + id + '/', function(data) {
        // console.log(data);
        var content;
        if (!$.isEmptyObject(data)) {
            content = makeTable(DETAIL_HEADERS[section], data, false, true);
        } else {
            content = $('<div/>', {text: 'No details.', 'class': 'no_tasks'});
        }
        content.addClass('details');
        var row = $('#' + section + id);
        row.find('td').animate({
            paddingTop: '3px',
            paddingBottom: '3px',
        }, 300);
        insertNewRow(row, content, animation)
            .attr('id', section + id + 'details');
        // $(sid + ' #' + id + 'details').addClass('data_row');
        row.addClass('expanded');
    });
}

function hideDetails(section, id) {
    state[section].detailsShowing[id] = false;
    var detail_id = '#' + section + id;
    row = $(detail_id + 'details');
    $(detail_id + ' td').animate({
        paddingTop: '1px',
        paddingBottom: '1px',
    }, 300);
    row.find('div').slideUp(300, function() {
        row.detach();
        $(detail_id).removeClass('expanded');
    });
}

function setupSection(section, data) {
    table = makeTable(HEADERS[section], data[section], [section, '']);
    table.addClass('data');
    // console.log(data);
    initDataTable(section, table);
    sid = '#' + section;
    $(sid + ' > table').replaceWith(table);
    table = table.children('tbody');
    if (data.page.next != 0) {
        // $('#daemons .next_page').css('display', 'inline');
        $(sid + ' .next_page').addClass('clickable').click(function() {
            refreshSection(section, {page : state.nextPage});
        });
        state.nextPage = data.page.next;
    } else {
        // $('#daemons .next_page').css('display', 'none');
        $(sid + ' .next_page').removeClass('clickable').unbind('click');
    }
    if (data.page.prev != 0) {
        // $('#daemons .prev_page').css('display', 'inline');
        $(sid + ' .prev_page').addClass('clickable').click(function() {
            refreshSection(section, {page : state.prevPage});
        });
        state.prevPage = data.page.prev;
    } else {
        $(sid + ' .prev_page').removeClass('clickable').unbind('click');
    }
}

function refreshSection(name, filters) {
    if (!filters) filters = {};
    if ('since' in filters) {
        state[name].since = filters.since;
    } else {
        filters.since = state[name].since;
    }
    $.get('/data/' + name + '/', filters, function(data) {
        setupSection(name, data);
    });
}

$(document).ready(function() {
    refreshSection('daemons');
    refreshSection('jobs');
    $('#timeframe span').addClass('clickable');
    $('#page_nav span').addClass('clickable');
});
