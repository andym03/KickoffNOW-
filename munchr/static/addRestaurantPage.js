var searchField = document.querySelector('#gPlacesSearch');
var formFields = document.querySelectorAll('.db-field');

var searchBox = new google.maps.places.SearchBox(searchField);

// Bias the SearchBox results towards current map's viewport.
map.addListener('bounds_changed', function() {
  searchBox.setBounds(map.getBounds());
});

searchBox.addListener('places_changed', function() {
    var places = searchBox.getPlaces();

    if (places.length > 1) {
        searchField.value = "Please enter a specific restaurant";
        searchField.select();
        return;
    } else if (places.length == 0) {
        searchField.value = "No results found";
        searchField.select();
        return;
    }

    searchField.value = places[0].name;

    // Check if we have something to fill into each of the form fields:
    for (var i = 0; i < formFields.length; i++) {

        switch (formFields[i].id) {
            case "name":
                formFields[i].value = places[0].name;
                break;
            case "imageURL":
                if (places[0].photos.length > 0) {
                    formFields[i].value = places[0].photos[0].getUrl({'maxWidth' : 640, 'maxHeight' : 480});
                }
                break;
            case "phone":
                if (places[0].hasOwnProperty("formatted_phone_number")) {
                    formFields[i].value = places[0].formatted_phone_number;
                }
                break;
            case "coordsX":
                formFields[i].value = places[0].geometry.location.lat();
                break;
            case "coordsY":
                formFields[i].value = places[0].geometry.location.lng();
                break;
            case "address":
                formFields[i].value = places[0].formatted_address;
                break;
            default:
                formFields[i].focus();

            break;
        }
    }

    infowindow = new google.maps.InfoWindow();
    var service = new google.maps.places.PlacesService(map);
    service.textSearch({
        query: searchField.value
    }, callback);

    function callback(results, status) {
      if (status === google.maps.places.PlacesServiceStatus.OK) {
        for (var i = 0; i < results.length; i++) {
            console.log(results[i]);
            createMarker(results[i]);
        }
      }
    }

    function createMarker(place) {
      var placeLoc = place.geometry.location;
      var marker = new google.maps.Marker({
        map: map,
        position: place.geometry.location
      });

      google.maps.event.addListener(marker, 'click', function() {
        infowindow.setContent(place.name);
        infowindow.open(map, this);
      });
    }

    map.setZoom(14);
    map.setCenter({lat : places[0].geometry.location.lat(), lng: places[0].geometry.location.lng()});

});
