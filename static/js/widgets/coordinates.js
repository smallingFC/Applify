$(document).ready(function() {
    'use strict'

    $('#id_coordinates').click(function() {
        $.getJSON("/api/coordinates/", { address: $('#id_location').val() })
        .done(function(resp) {
            // Update latitude and longitude
            $('#id_lat').val(resp.latitude);
            $('#id_lon').val(resp.longitude);
        })
        .fail(function(resp) {
            // Show user error message
            console.log(resp.responseText);
            alert(resp.responseText);
        });
    });
});
