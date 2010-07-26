
## Norc Release v1.0.1

### Features:
  - Added 'Failed Tasks' table, which shows all tasks with an error status.

### Tweaks:
  - Content is no longer centered.
  - display:table allows for intelligently sized content sections.
  - Clicking on a different task count cell now switches to showing those tasks, instead of just collapsing the details.
  - Fixed highlighting color of task count by status cells when the row is expanded.
  - The get_daemon_type hack in models.py no longer uses .count() for efficiency purposes.

### Bug Fixes:
  - Switched back a CSS class change that broke proper coloring of pagination.
  - Added the loading indicator to source control.
  - Improved how the indicator is displayed so that table cells don't get shifted.
  - An exception will be thrown if the NORC_ENVIRONMENT shell variable is not set.  Before it would default to 'BaseEnv', but since Django needs more settings than that to run, a custom environment is now enforced.


## Norc Release v1.0

### Features:
  - populate_db.py script in utils can fill your DB with large amounts of random data for testing.  Requires init_db to be run first from an empty database.
  - SINCE_FILTER dictionary in structures.py now allows a per data key definition of how to filter a data set using a since date.
  - ORDER dictionary in structures.py allows an optional per data key definition of how to order the results.
  - Added a map in status.js that allows customization of data tables.
  - Task selection by status: Click on the number of running/success/errored tasks for any daemon to reveal only those tasks.
  - Timestamp of the last full page refresh.
  - Loading indicator for any data retrieval.

### Tweaks:
  - Auto-reload is now disabled by default.
  - Hard-coded width of sqsqueues table to 50% (in status.css) to appease Darrell.

### Bug Fixes:
  - Subtables now reflect the correct timeframe (for real this time).
  - Removed erroneous reference in sqs/__init__.py to a test setting, SQSTASK_IMPLEMENTATIONS, that was not supposed to be committed.


## Norc Release v0.9

### Features:
  - Proper pagination of all subtables!
  - Highlighting of selected timeframe.
  - SQS Queue table now exists, with proper handling if SQS isn't enabled.
  - JSON response now uses a list, allowing for ordering of items.
  - Daemons are now ordered by descending time started.
  - There is now an auto-reload checkbox to disable it.
  - Middleware that lets you view the traceback of an exception caused by an AJAX request as plain text.

### Tweaks:
  - Default page size is now 20 for all table levels.
  - Detail tables with only one page no longer show the paging row.
  - Rows will no longer line-wrap; the table just grows horizontally.
  - More columns have been aligned properly.
  - Added ErrorHandlingMiddleware to the default middleware list.

### Bug Fixes:
  - Going from the nth page back to a timeframe with < n pages now works (goes back to the first page).
  - Options are now properly inherited from parent chains.  This means that subtables now reflect the selected timeframe.
  - Several other minor issues.
