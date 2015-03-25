(function(){
    var controllers = angular.module('rattleMediaControllers', []);

    controllers.controller('MusicController', ['$scope', '$http', function($scope, $http){
        console.log('controller loaded');
    }]);
})();