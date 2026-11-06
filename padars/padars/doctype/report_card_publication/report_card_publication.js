frappe.ui.form.on("Report Card Publication", {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.set_intro(__("This published version is retained permanently. Corrections require a new reviewed publication."));
    frm.add_custom_button(__("View Published Report"), () => {
      window.open(`/report-cards?publication=${encodeURIComponent(frm.doc.name)}`, "_blank", "noopener");
    });
    frm.add_custom_button(__("Download PDF"), () => {
      window.open(`/api/method/padars.publication.download_report_card?publication=${encodeURIComponent(frm.doc.name)}`, "_blank", "noopener");
    });
  },
});
