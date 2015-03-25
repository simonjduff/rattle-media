(function(){
    var app = angular.module('rattleMediaApp', ['ngRoute', 'rattleMediaControllers']);
    app.config(['$routeProvider', function($routeProvider){
        $routeProvider.
            when('/', {
                templateUrl: 'partials/music.html',
                controller: 'MusicController'
            });
    }]);
})();