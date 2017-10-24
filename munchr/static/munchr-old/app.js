var app = angular.module("FoodLook", []);
app.controller("MainController", function($scope){
  $scope.page = 'login'
  $scope.categories = [false, false, false, false, false, false]
  $scope.bookmarks = [true, true, true, true, true, true]
  $scope.suggestion = 'hsp-1'
  $scope.foodCard = 'hsp-1'
  $scope.orderState='order'
});
