(function(){
    var controllers = angular.module('rattleMediaControllers', []);

    controllers.controller('MusicController', ['$scope', '$http', 'socketio', function($scope, $http, socketio){
        $scope.search = function(){
            socketio.emit('my event', 'data');
        }

        socketio.on('my response', function(data){
            );
        });
    }]);
})();