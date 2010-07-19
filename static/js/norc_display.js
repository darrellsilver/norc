
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
    tasks: ['ID', 'Job', 'Task', 'Started', 'Ended', 'Status'],
    sqstasks: ['ID', 'Task ID', 'Started', 'Ended', 'Status'],
    iterations: ['Iter ID', 'Type', 'Started', 'Ended', 'Status'],
};

var DETAIL_KEYS = {
    daemons: 'tasks',
    sqsdaemons: 'sqstasks',
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
    detailsShowing: {},
    // The last timeframe selection.
    since: {},
    nextPage: {},
    prevPage: {},
    data: {},
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

function chainLength(chain) {
    return chain.split('-').length;
}

// Takes a string like 'x-y-z' and returns 'z'.
function getKeyFromChain(chain) {
    return chain.split('-').slice(-1);
}

// Takes a string like 'x-y-z' and returns 'x-y'.
function getChainRemainder(chain) {
    return chain.split('-').slice(0, -1).join('-');
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
    var dataKey = getKeyFromChain(chain);
    var table = $('<table/>');
    table.addClass('L' + chainLength(chain));
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
            if (state.detailsShowing[rID]) {
                showDetails(chain, id, false);
            }
        };
        table.append(row);
    });
    table.children('tbody').children('tr:even').addClass('even');
    table.children('tbody').children('tr:odd').addClass('odd');
    return table;
}

function toggleDetails(chain, id) {
    if (state.detailsShowing[chain + '-' + id]) {
        hideDetails(chain, id);
    } else {
        showDetails(chain, id, true);
    }
}

function showDetails(chain, id, slide) {
    var idChain = chain + '-' + id;
    state.detailsShowing[idChain] = true;
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    retrieveData(chain, id, {}, function(content, data) {
        var row = $('#' + idChain);
        if (slide) {
            row.find('td').animate({
                paddingTop: '3px',
                paddingBottom: '3px',
            }, 300);
        } else {
            row.find('td').css({
                paddingTop: '3px',
                paddingBottom: '3px',
            });
        }
        insertNewRow(row, content, slide).addClass('details')
            .attr('id', [chain, id, detailKey].join('-'));
        row.addClass('expanded');
    });
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
    if (!filters) filters = {};
    if ('since' in filters) {
        state.since[chain] = filters.since;
    } else  if (chain in state.since) {
        filters.since = state.since[chain];
    } else {
        filters.since = 'all'
    }
    var path = '/data/' + dataKey + '/';
    if (id != false) {
        path += id + '/';
        dataKey = DETAIL_KEYS[dataKey];
        // Turrible haxxorz to make SQS shit work.
        if (dataKey == 'tasks' && chain == 'daemons'
                               && state.data[chain][id]['type'] == 'SQS') {
            dataKey = 'sqstasks';
        }
        chain = chain + '-' + dataKey;
    }
    $.get(path, filters, function(data) {
        // This is currently only used for fixing SQS tasks.
        if (id != false) {
            state.data[getChainRemainder(chain) + '-' + id] = data[dataKey];
        } else {
            state.data[chain] = data[dataKey];
        }
        var content;
        if (!$.isEmptyObject(data[dataKey])) {
            content = makeDataTable(chain, data[dataKey], id != false);
        } else if (chainLength(chain) == 1) {
            content = makeDataTable(chain, data[dataKey], id != false);
            insertNewRow(content.find('tr:first'), $('<div/>', {
                'text': 'No ' + dataKey + '.', 
                'class': 'noDetails',
            }));
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
        content.addClass('data');
        var sID = '#' + dataKey + '-section';
        $(sID + ' > .data').replaceWith(content);
        if (data.page.next != 0) {
            $(sID + ' .next_page').addClass('clickable').unbind('click').click(function() {
                refreshSection(dataKey, {page : state.nextPage});
            });
            state.nextPage = data.page.next;
        } else {
            $(sID + ' .next_page').removeClass('clickable').unbind('click');
        }
        if (data.page.prev != 0) {
            $(sID + ' .prev_page').addClass('clickable').unbind('click').click(function() {
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

// function 

$(document).ready(function() {
    SECTIONS = ['daemons', 'jobs'];
    $.each(SECTIONS, function(i, section) {
        refreshSection(section);
        makeTimeOptions(section);
    });
    $('.timeframe span').addClass('clickable');
    $('.pages span').addClass('clickable');
    refresh = function() {
        $.each(SECTIONS, function(i, section) {
            refreshSection(section);
        });
        setTimeout(refresh, 60000);
    };
    setTimeout(refresh, 60000);
});
