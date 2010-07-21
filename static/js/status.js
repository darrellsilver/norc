
// TODO: Fix double-clicking sometimes opening two details tables.
// TODO: Sorting (sorttables?)
// TODO: Log viewing.
// TODO: Daemon interactive control.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation
// TODO: Comment this file. (javadoc style?)


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
    sqsqueues: ['Name', 'Num Items', 'Timeout'],
};

var DETAIL_KEYS = {
    daemons: 'tasks',
    jobs: 'iterations',
    iterations: 'tasks',
};

var STYLE_BY_COLUMN = {
    'region': 'leftAlign',
    'running': 'rightAlign',
    'success': 'rightAlign',
    'errored': 'rightAlign',
};
// The data keys for which statuses should be colored.
var HAS_STATUS_COLOR = ['tasks', 'sqstasks'];
// Map of statuses to their style classes.
var STATUS_CSS_CLASSES = {
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
    // Paging data; next page and previous page numbers.
    prevPage: {},
    page: {},
    nextPage: {},
    per_page: {},
    type: {},
    data: {},
};


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

// Chain utilities!  Chains are the strings of the form 'x-y-z' that are used
// throughout this file in order to track what section is being operated on.


function chainLength(chain) {
    if (chain == '') return 0;
    return chain.split('-').length;
}

// Takes a string like 'x-y-z' and returns 'z'.
function getKeyFromChain(chain, i) {
    if (!i) i = 1;
    return chain.split('-').slice(-i)[0];
}

// Takes a string like 'x-y-z' and returns 'x-y'.
function getChainRemainder(chain, i) {
    if (!i) i = 1;
    return chain.split('-').slice(0, -i).join('-');
}

function chainJoin() {
    var acc = arguments[0];
    for (var i = 1; i < arguments.length; i++) {
        acc += '-' + arguments[i];
    }
    return acc ? acc : '';
    // return Array.prototype.slice.call(arguments).join('-');
}

// Inserts a new row after rowAbove with the given ID and
// contents using the given animation (defaults to slideDown).
function insertNewRow(rowAbove, contents, slide) {
    var row = $('<tr/>').addClass('inserted');
    var div = $('<div/>').css('display', 'none');
    $.each(contents, function (i, c) {
        div.append(c);
    });
    row.append($('<td/>').attr('colspan',
        rowAbove.children('td').length).append(div));
    rowAbove.after(row);
    if (slide) {
        row.find('div:first').slideDown(300);
    } else {
        row.find('div:first').css('display', '');
    }
    return row;
}

/*********************
    Core Functions
*********************/

// Creates a table.
function makeDataTable(chain, data) {
    
    var dataKey = getKeyFromChain(chain);
    var table = $('<table/>');
    // Data tables have class L<n> to reflect being n layers deep in the tree.
    table.addClass('L' + chainLength(chain));
    if (!$.isEmptyObject(data)) {   // Make the header if there is data.
        var hRow = $('<tr/>');
        var headers = DATA_HEADERS[dataKey];
        $.each(headers, function(i, h) {
            hRow.append($('<th/>').append(h));
        });
        table.append(hRow);
    } else {
        table.append($('<tr><td>No ' + dataKey + '.</td></tr>'));
    }
    $.each(data, function(i, rowData) {
        // Make the row and add the ID cell.
        var id = rowData['id'];
        // console.log(id);
        var rID = chain + '-' + id;
        var row = $('<tr/>').attr('id', rID);//.append($('<td/>').append(id));
        $.each(headers.map(unTitle), function(j, header) {
            if (j == 0) header = 'id';
            var cell = $('<td/>').append(rowData[header]);
            if (header in STYLE_BY_COLUMN) {
                cell.addClass(STYLE_BY_COLUMN[header]);
            }
            if (header == 'status' &&
                    HAS_STATUS_COLOR.indexOf(dataKey) != -1) {
                cell.addClass(STATUS_CSS_CLASSES[rowData['status']]);
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

function makePagination(chain) {
    var ul = $('<ul/>').addClass('pagination');
    var prev = $('<li>Prev</li>').addClass('prev').click(function() {
        if (state.prevPage[chain] > 0) {
            turnPage(chain, state.prevPage[chain]);
        }
    });
    var curr = $('<li/>').addClass('page');
    var next = $('<li>Next</li>').addClass('next').click(function() {
        if (state.nextPage[chain] > 0) {
            turnPage(chain, state.nextPage[chain]);
        }
    });
    ul.append(prev).append(curr).append(next);
    return ul;
}

function updatePagination(chain, pageData) {
    state.nextPage[chain] = pageData.nextPage;
    state.prevPage[chain] = pageData.prevPage;
    var base = $('#' + chain);
    if (pageData.nextPage > 0) {
        base.find('.next').addClass('clickable');
    } else {
        base.find('.next').removeClass('clickable');
    }
    if (pageData.prevPage > 0) {
        base.find('.prev').addClass('clickable');
    } else {
        base.find('.prev').removeClass('clickable');
    }
    base.find('.page').text(pageData.current + ' of ' + pageData.total);
}

function turnPage(chain, page) {
    var origTable = $('#' + chain + ' table:first');
    var newChain = chain;
    var id = 0;
    if (chainLength(chain) > 1) {
        id = getKeyFromChain(chain, 2);
        newChain = getChainRemainder(chain, 2);
    }
    retrieveData(newChain, id, {'page': page}, function(data, table) {
        origTable.replaceWith(table);
        updatePagination(chain, data.page);
    });
}

function toggleDetails(chain, id) {
    if (state.detailsShowing[chain + '-' + id]) {
        hideDetails(chain, id);
    } else {
        showDetails(chain, id, true);
    }
}

function showDetails(chain, id, slide) {
    var idChain = chainJoin(chain, id);
    state.detailsShowing[idChain] = true;
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    retrieveData(chain, id, {per_page: 5}, function(data, table) {
        var row = $('#' + idChain).addClass('expanded');
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
        // Add the detail key to the chain so the pagination functions
        // find the right row to work with.
        chain = chainJoin(idChain, detailKey);
        // var hasData = !$.isEmptyObject(data.data);
        var hasData = data.data != [];
        var contents = [table, hasData ? makePagination(chain) : $('')];
        insertNewRow(row, contents, slide).attr('id', chain);
        if (hasData) updatePagination(chain, data.page);
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

function initOptions(chain, options) {
    if (!options) options = {};
    var fields = ['since', 'page', 'per_page'];
    // The fields which should inherit options
    var inherit = ['since'];
    $.each(fields, function(i, o) {
        if (o in options) {
            state[o][chain] = options[o];
        } else if (o in inherit) {
            var searchChain = chain;
            while (chainLength(searchChain) > 0) {
                if (searchChain in state[o]) {
                    options[o] = state[o][searchChain];
                    break;
                } else {
                    searchChain = getChainRemainder(searchChain);
                }
            }
        } else if (chain in state[o]) {
            options[o] = state[o][chain];
        }
    });
    return options;
}

function retrieveData(chain, id, options, callback) {
    var dataKey = getKeyFromChain(chain);
    options = initOptions(id ? chainJoin(chain, id) : chain, options);
    var path = '/data/' + dataKey + '/';
    if (id) {
        path += id + '/';
        dataKey = DETAIL_KEYS[dataKey];
        // Turrible haxxorz (hardcoding) to make SQS shit work.
        // debugger;
        if (dataKey == 'tasks' && chain == 'daemons') {
            var obj = state.data[chain].filter(function(k) {
                return k.id == id;
            })[0];
            if (obj['type'] == 'SQS') {
                dataKey = 'sqstasks';
            }
        }
        chain = chainJoin(chain, dataKey);
    }
    $.get(path, options, function(data) {
        // console.log(data);
        // This is currently only used for fixing SQS tasks.
        if (id) {
            state.data[chainJoin(
                getChainRemainder(chain), id)] = data.data;
        } else {
            state.data[chain] = data.data;
        }
        callback(data, makeDataTable(chain, data.data));
    });
}

function refreshSection(dataKey, options) {
    retrieveData(dataKey, false, options, function(data, table) {
        var sID = '#' + dataKey;
        $(sID + ' > table').replaceWith(table);
        updatePagination(dataKey, data.page);
    });
}

/*********************
    Initialization
*********************/

function initSection(dataKey) {
    var section = '#' + dataKey;
    // $(section + ' .timeframe').before(
    //     $('<span>Within</span>').css('width', '45px'));
    $.each(TIME_OPTIONS, function(i, timeString) {
        var tfLink = $('<li/>').append(timeString).addClass('clickable');
        if (timeString == '10m') tfLink.addClass('selected');
        tfLink.click(function() {
            $(this).siblings().removeClass('selected');
            $(this).addClass('selected');
            refreshSection(dataKey, {'since': timeString});
        });
        $(section + ' .timeframe').append(tfLink);
    });
    $(section).append(makePagination(dataKey));
}

$(document).ready(function() {
    var SECTIONS = ['daemons', 'jobs'];
    if (SQS_ENABLED) SECTIONS.push('sqsqueues');
    $.each(SECTIONS, function(i, section) {
        initSection(section);
        refreshSection(section);
    });
    refresh = function() {
        $.each(SECTIONS, function(i, section) {
            refreshSection(section);
        });
        setTimeout(refresh, 60000);
    };
    // setTimeout(refresh, 60000);
});
