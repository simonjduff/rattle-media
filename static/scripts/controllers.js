(function(){
    var controllers = angular.module('rattleMediaControllers', []);

    controllers.controller('MusicController', ['$scope', '$http', 'socketio', function($scope, $http, socketio){
        $scope.searchSubmit = function(){
            socketio.emit('search', $scope.searchText);
        }

        socketio.on('search complete', function(searchResults){
            $scope.searchResults = searchResults;
        });
    }]);
})();