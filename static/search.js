var searchField = document.querySelector('#gPlacesSearch');
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
