/* Javascript for OneDriveXBlock. */
function OneDriveXBlock(runtime, element) {


    $(function ($) {
        /* Here's where you'd do things on page load. */
        //alert('page load');
        require.config({
            paths: {
                "onedrive": "https://js.live.net/v6.0/OneDrive"
            }
        });
    });
}
