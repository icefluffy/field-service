# List Dropdowns Open on First Click

In Odoo's editable lists, the first click on a row only switches the row to edit
mode, so a dropdown needed a second click. With this module installed, one click
or tap opens it, in every editable list of the database:

- selection fields (and many2one fields shown with `widget="selection"`) use
  Odoo's own dropdown instead of the browser's, so it can be opened directly,
  also on iPad/Safari; long lists (more than 10 options) get a search box;
- many2one and tag fields open their suggestion list on the first click.

Forms are unchanged (their dropdowns already open on the first click).
