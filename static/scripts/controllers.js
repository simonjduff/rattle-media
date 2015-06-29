(function(){
    var controllers = angular.module('rattleMediaControllers', []);

    controllers.controller('MusicController', ['$scope', '$http', 'socketio', function($scope, $http, socketio){
        $scope.searchSubmit = function(){
            socketio.emit('search', $scope.searchText);
        }

        socketio.on('search complete', function(searchResults){
            $scope.searchResults = searchResults;
        });

        socketio.on('state change', function(new_state){
            console.log('Changing state to ' + new_state);
            $scope.state = new_state;
        });

        $scope.playSong = function(songId){
            console.log('playing song ' + songId);
            socketio.emit('play song', songId);
        }

        $scope.stopPlaying = function(){
            socketio.emit('stop');
        }

        $scope.togglePlayback = function(){
            socketio.emit('toggle playback');
        }

        $scope.playAlbum = function(albumId){
            socketio.emit('play album', albumId);
        }
    }]);

    controllers.directive('rattleArtists', function(){
        return{
            templateUrl: 'partials/artists.html'
        }
    });

    controllers.directive('rattleAlbums', function(){
        return{
            templateUrl: 'partials/albums.html'
        }
    });

    controllers.directive('rattleTracks', function(){
        return{
            templateUrl: 'partials/tracks.html'
        }
    });
})();