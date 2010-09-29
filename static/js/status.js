
// TODO: Log viewing.
// TODO: Historical error rates (caching in db) for a region or job or status.
//       Average run time for each status.  Distribution... standard deviation
// TODO: Comment this file. (javadoc style?)

/****************
    Constants
****************/

String.format = function() {
  var s = arguments[0];
  for (var i = 0; i < arguments.length - 1; i++) {       
    var reg = new RegExp("\\{" + i + "\\}", "gm");             
    s = s.replace(reg, arguments[i + 1]);
  }

  return s;
}

function pad(n, i) {
    var s = n.toString();
    while (s.length < i) {
        s = '0' + s;
    }
    return s;
}

function formatDate(date) {
    return  pad(date.getFullYear(), 4) + '/' +
            pad(date.getMonth(), 2) + '/' +
            pad(date.getDate(), 2) + ' ' +
            pad(date.getHours(), 2) + ':' +
            pad(date.getMinutes(), 2) + ':' +
            pad(date.getSeconds(), 2)
}

var DETAIL_KEYS = {
    daemons: 'instances',
    tasks: 'instances',
};

var STYLE_BY_COLUMN = {
    'leftAlign': ['region', 'name', 'host'],
    'rightAlign': ['running', 'success', 'errored', 'pid', 'num_items'],
};

// The data keys for which statuses should be colored.
var HAS_STATUS_COLOR = ['tasks', 'sqstasks', 'failedtasks'];

var HAS_LOGS = {
    'daemons': 'daemons',
    'instances': 'instances',
    'tasks': 'tasks',
    'sqstasks': 'sqstasks',
    'failedtasks': 'tasks',
};

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
    'detailsShowing': {},
    // The last timeframe selection.
    'since': {
        'daemons': '10m',
        'failedtasks': 'all',
    },
    // Paging data; next page and previous page numbers.
    'prevPage': {},
    'nextPage': {},
    // Data request options.
    'page': {},
    'per_page': {},
    // Data cache; unnecessary except for the need to know daemon types.
    'data': {},
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

// Containment test for lists, since 'x in y' doesn't work with them.
function isIn(element, list_) {
    return list_.indexOf(element) >= 0;
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

function makeDaemonControls(id) {
    var div = $('<div/>').addClass('slideout');
    var ul = $('<ul/>');
    $.each(['pause', 'stop', 'kill', 'salvage', 'delete'], function(i, v) {
        var li = $('<li/>').text(v);
        li.click(function() {
            var reply = prompt('Are you sure you want to try to ' +
                v + ' daemon ' + id + '?  If so, type "' + v + '" below.');
            if (reply == v) {
                var path = '/control/daemon/' + id + '/';
                $.post(path, {'do': v}, function(data) {
                    if (data == true) {
                        reloadSection('daemons');
                    }
                });
            }
        });
        ul.append(li);
    });
    return div.append(ul);
}

var TABLE_CUSTOMIZATION = {
    daemons: function(chain, id, header, cell, row) {
        if (!row.data('click_rewritten')) {
            row.unbind('click');
            row.click(function() {
                if (!row.data('overruled')) {
                    row.children('td').removeClass('selected');
                    toggleDetails(chain, id);
                }
            });
            row.data('click_rewritten', true);
        }
        if (isIn(header, ['running', 'succeeded', 'failed'])) {
            cell.addClass('clickable');
            cell.click(function() {
                if (cell.hasClass('selected')) {
                    cell.removeClass('selected');
                    hideDetails(chain, id);
                } else {
                    cell.siblings().removeClass('selected');
                    cell.addClass('selected');
                    showDetails(chain, id, true, {status: header});
                }
            });
            cell.hover(function() {
                row.data('overruled', true);
            }, function() {
                row.data('overruled', false);
            });
        } else if (header == 'status' && IS_SUPERUSER) {
            cell.addClass('clickable');
            var controls = makeDaemonControls(id);
            cell.hover(function() {
                row.data('overruled', true);
                var ul = controls.find('ul');
                cell.append(controls);
                ul.animate({width: 'hide'}, 0);
                ul.animate({width: 'show'}, 300);
            }, function() {
                row.data('overruled', false);
                controls.find('ul').animate({width: 'hide'}, 0, function() {
                    controls.detach();
                });
            });
        }
    },
};

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
        var unTitledHeaders = headers.map(unTitle);
        // Make the row and add the ID cell.
        var id = rowData.id;
        var rID = chain + '-' + id;
        var row = $('<tr/>').attr('id', rID);
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
        $.each(unTitledHeaders, function(j, header) {
            var cell = $('<td/>').append(rowData[header]);
            $.each(STYLE_BY_COLUMN, function(cls, hs) {
                if (isIn(header, hs)) cell.addClass(cls);
            })
            if (dataKey in TABLE_CUSTOMIZATION) {
                TABLE_CUSTOMIZATION[dataKey](chain, id, header, cell, row);
            }
            if (header == 'status') {
                if (isIn(dataKey, HAS_STATUS_COLOR)) {
                    cell.addClass(STATUS_CSS_CLASSES[rowData['status']]);
                }
                if (dataKey in HAS_LOGS) {
                    cell.addClass('clickable')
                    cell.click(function() {
                        window.open(
                            'logs/' + HAS_LOGS[dataKey] + '/' + id,
                            HAS_LOGS[dataKey] + '-' + id + '-log',
                            'menubar=no, innerWidth=700, innerHeight=700')
                    });
                }
            }
            row.append(cell);
        });
        
        table.append(row);
    });
    table.children('tbody').children('tr:even').addClass('even');
    table.children('tbody').children('tr:odd').addClass('odd');
    return table;
}

function makePagination(chain) {
    var ul = $('<ul/>').addClass('pagination');
    var prev = $('<li/>').addClass('prev').click(function() {
        if (state.prevPage[chain] > 0) {
            turnPage(chain, state.prevPage[chain]);
        }
    });
    var curr = $('<li/>').addClass('page');
    var next = $('<li/>').addClass('next').click(function() {
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
    if (pageData.total > 1) {
        base.find('.page').text(pageData.current + ' of ' + pageData.total);
        var prev = base.find('.prev').text('Prev');
        var next = base.find('.next').text('Next');
        if (pageData.prevPage > 0) {
            prev.addClass('clickable');
        } else {
            prev.removeClass('clickable');
        }
        if (pageData.nextPage > 0) {
            next.addClass('clickable');
        } else {
            next.removeClass('clickable');
        }
    } else {
        base.find('.next').removeClass('clickable').text('');
        base.find('.page').text('');
        base.find('.prev').removeClass('clickable').text('');
    }
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

function showDetails(chain, id, slide, options) {
    if (!options) options = {};
    var idChain = chainJoin(chain, id);
    state.detailsShowing[idChain] = true;
    var detailKey = DETAIL_KEYS[getKeyFromChain(chain)];
    retrieveData(chain, id, options, function(data, table) {
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
        var initRow = function() {
            var contents = [table];
            if (data.page.total > 1) contents.push(makePagination(chain));
            insertNewRow(row, contents, slide).attr('id', chain);
            if (data.page.total > 1) updatePagination(chain, data.page);
        };
        if ($('#' + chain).length > 0) {
            $('#' + chain + ' div:first').slideUp(200, function() {
                $('#' + chain).remove();
                initRow();
            });
        } else {
            initRow();
        }
    });
}

function hideDetails(chain, id) {
    var idChain = chain + '-' + id;
    state.detailsShowing[idChain] = false;
    state.prevPage[idChain] = undefined;
    state.nextPage[idChain] = undefined;
    state.page[idChain] = undefined;
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
        } else if (isIn(o, inherit)) {
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

function makeLoadingIndicator() {
    return $('<img src="/static/images/spinner.gif" alt="spinner"/>').attr({
        src: '/static/images/spinner.gif', alt: 'loading...',
    });
}

function retrieveData(chain, id, options, callback) {
    var dataKey = getKeyFromChain(chain);
    options = initOptions(id ? chainJoin(chain, id) : chain, options);
    var loading = makeLoadingIndicator();
    var path = '/data/' + dataKey + '/';
    if (id) {
        loading = $('<tr/>').addClass('loading').append(loading);
        $('#' + chain + '-' + id).before(loading);
        path += id + '/' + DETAIL_KEYS[dataKey] + '/';
        dataKey = DETAIL_KEYS[dataKey];
        chain = chainJoin(chain, dataKey);
    } else {
        loading = $('<span/>').addClass('loading').append(loading);
        $('#' + chain).find('h2').after(loading);
    }
    loading.ajaxComplete(function(e, xhr, settings) {
        if (settings.url.substr(0, path.length) == path) {
            $(this).remove();
        }
    });
    $.get(path, options, function(data) {
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

function reloadSection(dataKey, options) {
    retrieveData(dataKey, false, options, function(data, table) {
        $('#' + dataKey + ' > table').replaceWith(table);
        updatePagination(dataKey, data.page);
    });
}

/*********************
    Initialization
*********************/

function initSection(dataKey) {
    var section = $('#' + dataKey);
    if (dataKey in state.since && isIn(state.since[dataKey], TIME_OPTIONS)) {
        var timeframe = $('<ul/>').addClass('timeframe');
        $.each(TIME_OPTIONS, function(i, timeString) {
            var t = $('<li/>').append(timeString).addClass('clickable');
            if (timeString == state.since[dataKey]) t.addClass('selected');
            t.click(function() {
                $(this).siblings().removeClass('selected');
                $(this).addClass('selected');
                delete state.page[dataKey];
                reloadSection(dataKey, {'since': timeString});
            });
            timeframe.append(t);
        });
        section.find('table:first').before(timeframe);
    }
    $(section).append(makePagination(dataKey));
}

$(document).ready(function() {
    // var SECTIONS = ['daemons', 'jobs', 'failedtasks'];
    $.each(SECTIONS, function(i, section) {
        initSection(section);
    });
    var reloadAll = function() {
        $.each(SECTIONS, function(i, section) {
            reloadSection(section);
        });
        $('#timestamp').text('Last updated at: ' + formatDate(new Date()));
    };
    reloadAll()
    $('#auto-reload input').attr('checked', false).click(function() {
        if (this.checked == true) {
            reloadAll();
            state.autoReloadIID = setInterval(reloadAll, 60000);
        } else {
            clearInterval(state.autoReloadIID);
            delete state.autoReloadIID;
        }
    });
});
