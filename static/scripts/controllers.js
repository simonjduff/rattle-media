(function(){
    var controllers = angular.module('rattleMediaControllers', []);

    controllers.controller('MusicController', ['$scope', '$http', 'socketio', function($scope, $http, socketio){
        $scope.search = function(){
            console.log($scope.searchText)
            socketio.emit('search', $scope.searchText);
        }

        socketio.on('search complete', function(searchResults){
            console.log(searchResults);
        });
    }]);
})();