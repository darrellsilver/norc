
// TODO: Fix double-clicking sometimes opening two details tables.
// TODO: Sorting (sorttables?)
// TODO: Log viewing.
// TODO: Daemon interactive control.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation
// TODO: Comment this file. (javadoc style?)
// TODO              


/****************
    Constants
****************/

// ATTN: The names of these headers are unTitle'd and then used directly
//       to pull data from JSON objects; changing them here requires a
//       change on the backend as well or stuff will break.
var DATA_HEADERS = {
    daemons: ['ID', 'Type', 'Region', 'Host', 'PID', 'Running',
        'Success', 'Errored', 'Started', 'Ended', 'Status'],
    jobs: ['Job ID', 'Name', 'Description', 'Added'],
    tasks: ['Task ID', 'Job', 'Task', 'Started', 'Ended', 'Status'],
    iterations: ['Iter ID', 'Type', 'Started', 'Ended', 'Status'],
};

var DETAIL_KEYS = {
    daemons: 'tasks',
    jobs: 'iterations',
    iterations: 'tasks',
}
// The data keys for which statuses should be colored.
var HAS_STATUS_COLOR = ['tasks'];
// Map of statuses to their style classes.
var STATUS_CSS_MAP = {
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
var TIME_OPTIONS = ['10m', '30m', '1h', '3h', '12h', '1d', '7d', 'all'];

// Saved state of the page.
var state = {
    // Whether details are showing for a row.
    detailsShowing : {},
    'daemons' : {
        
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

// Takes a string like 'x-y-z' and returns 'z'.
function getKeyFromChain(str) {
    return str.split('-').slice(-1);
}

// Takes a string like 'x-y-z' and returns 'x-y'.
function getChainRemainder(str) {
    return str.split('-').slice(0, -1).join('-');
}

// Inserts a new row after rowAbove with the given ID and
// contents using the given animation (defaults to slideDown).
function insertNewRow(rowAbove, contents, slide) {
    var row = $('<tr><td><div></div></td></tr>');
    row.find('td').attr('colspan', rowAbove.children('td').length)
        .find('div').css('display', 'none').append(contents);
    rowAbove.after(row);
    if (slide) {
        row.find('div:first').slideDown(300);
    } else {
        row.find('div:first').css('display', '')
    }
    return row;
}

/*********************
    Core Functions
*********************/

// Creates a table.
function makeDataTable(chain, data, details) {
    console.log(chain);
    var dataKey = getKeyFromChain(chain);
    var table = $('<table/>');
    table.addClass('L' + chain.split('-').length);
    var hRow = $('<tr/>');
    var headers = DATA_HEADERS[dataKey];
    $.each(headers, function(i, h) {
        hRow.append($('<th/>').append(h));
    });
    table.append(hRow);
    $.each(data, function(id, rowData) {
        // Make the row and add the ID cell.
        var rID = chain + '-' + id;
        var row = $('<tr/>').attr('id', rID).append($('<td/>').append(id));
        $.each(headers.map(unTitle).slice(1), function(i, h) {
            var cell = $('<td/>').append(rowData[h]);
            if (h == 'status' && HAS_STATUS_COLOR.indexOf(dataKey) != -1) {
                cell.addClass(STATUS_CSS_MAP[rowData['status']]);
            }
            row.append(cell);
        });
        if (DETAIL_KEYS[dataKey]) {
            row.hover(function() {
                $(this).addClass('hover');
            }, function() {
                $(this).removeClass('hover');
            });
            row.click(function() {
                toggleDetails(chain, id);
            });
        };
        if (state.detailsShowing[rID]) {
            showDetails(chain, id, false);
        }
        table.append(row);
    });
    table.children('tbody').children('tr:even').addClass('even');
    table.children('tbody').children('tr:odd').addClass('odd');
    return table;
}

function toggleDetails(chain, id) {
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    if ($('#' + chain + '-' + id + '-' + detailKey).length > 0) {
        hideDetails(chain, id);
    } else {
        showDetails(chain, id, true);
    }
}

function showDetails(chain, id, slide) {
    state.detailsShowing[chain + '-' + id] = true;
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    retrieveData(chain, id, {}, function(content, data) {
        // content.addClass('details');
        var row = $('#' + chain + '-' + id);
        if (slide) {
            row.find('td').animate({
                paddingTop: '3px',
                paddingBottom: '3px',
            }, 300);
        } else {
            row.find('td').attr({
                paddingTop: '3px',
                paddingBottom: '3px',
            });
        }
        insertNewRow(row, content, slide).addClass('details')
            .attr('id', [chain, id, detailKey].join('-'));
        // $(sID + ' #' + id + 'details').addClass('data_row');
        row.addClass('expanded');
    });
    // $.get('/data/' + getKeyFromChain(chain) + '/' + id + '/', function(data) {
    //     var content;
    //     if (!$.isEmptyObject(data)) {
    //         content = makeDataTable(detailKey, data, parent);
    //     } else {
    //         content = $('<div/>', {
    //             'text': 'No ' + detailKey + '.', 
    //             'class': 'noDetails',
    //         });
    //     }
    //     
    // });
}

function hideDetails(chain, id) {
    state.detailsShowing[chain + '-' + id] = false;
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    var parentRowID = '#' + chain + '-' + id;
    $(parentRowID).children('td').animate({
        paddingTop: '1px',
        paddingBottom: '1px',
    }, 300);
    var row = $(parentRowID + '-' + detailKey);
    row.find('div').slideUp(300, function() {
        row.remove();
        $(parentRowID).removeClass('expanded');
    });
}

function retrieveData(chain, id, filters, callback) {
    var dataKey = getKeyFromChain(chain);
    // var parentChain = getChainRemainder(chain);
    // console.log(chain);
    // console.log(id);
    if (!filters) filters = {};
    // if ('since' in filters) {
    //     state[dataKey].since = filters.since;
    // } else {
    //     filters.since = state[dataKey].since;
    // }
    var path = '/data/' + dataKey + '/';
    if (id != false) {
        path += id + '/';
        dataKey = DETAIL_KEYS[dataKey];
        chain = chain + '-' + dataKey;
    }
    // console.log(path);
    $.get(path, filters, function(data) {
        var content;
        if (!$.isEmptyObject(data[dataKey])) {
            content = makeDataTable(chain, data[dataKey], id != false);
        } else {
            content = $('<div/>', {
                'text': 'No ' + dataKey + '.', 
                'class': 'noDetails',
            });
        }
        callback(content, data);
    });
}

function refreshSection(dataKey, filters) {
    retrieveData(dataKey, false, filters, function(content, data) {
        // console.log(dataKey);
        content.addClass('data');
        var sID = '#' + dataKey + '-section';
        $(sID + ' > .data').replaceWith(content);
        if (data.page.next != 0) {
            $(sID + ' .next_page').addClass('clickable').click(function() {
                refreshSection(dataKey, {page : state.nextPage});
            });
            state.nextPage = data.page.next;
        } else {
            $(sID + ' .next_page').removeClass('clickable').unbind('click');
        }
        if (data.page.prev != 0) {
            $(sID + ' .prev_page').addClass('clickable').click(function() {
                refreshSection(dataKey, {page : state.prevPage});
            });
            state.prevPage = data.page.prev;
        } else {
            $(sID + ' .prev_page').removeClass('clickable').unbind('click');
        }
    });
}

/*********************
    Initialization
*********************/

function makeTimeOptions(dataKey) {
    $.each(TIME_OPTIONS, function(i, t) {
        var link = $('<span/>').append(t).addClass('clickable').click(function() {
            refreshSection(dataKey, {'since': t});
        });
        $('#' + dataKey + '-section .timeframe').append(' ').append(link);
    });
}

$(document).ready(function() {
    refreshSection('daemons');
    makeTimeOptions('daemons');
    refreshSection('jobs');
    makeTimeOptions('jobs');
    $('.timeframe span').addClass('clickable');
    $('#page_nav span').addClass('clickable');
});
