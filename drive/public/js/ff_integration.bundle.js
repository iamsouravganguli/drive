import FileUploaderComponent from "./FileUploader.vue";
import BorDriveLogo from "./BorDriveLogo.vue";
import { createApp } from "vue";

DRIVE_UPLOADER = {
  label: "Drive",
  icon: BorDriveLogo,
  action: async ({ dialog, uploader, ...obj }) => {
    dialog.hide();
    const d = new bor.ui.Dialog({
      title: "Upload from Bor Drive",
      primary_action_label: "Upload",
      primary_action() {
        file = component.selected_node;
        uploader.upload_file({
          file_url: `/api/method/drive.api.files.get_file_content?entity_name=${file.value}`,
          private: file.share_count === -2 ? 0 : 1,
          file_name: file.label,
          ...obj,
        });
        return d.hide();
      },
    });

    // Fetch all teams first
    const teamsResp = await bor.call("drive.api.permissions.get_teams");
    const teams = teamsResp.message || [];
    if (!teams.length) {
      return bor.msgprint(__("No teams available"));
    }
    let app = createApp(FileUploaderComponent);
    const component = app.mount(d.body);
    d.show();
  },
};

(async () => {
  await bor.require("file_uploader.bundle.js");
  if (bor.ui.FileUploader?.UploadOptions)
    bor.ui.FileUploader.UploadOptions.push(DRIVE_UPLOADER);
})();
