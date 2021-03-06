
import xbmcaddon,xbmcgui,xbmcplugin,xbmc,requests,sys
import time,logging,re,json
import cache
from general import call_trakt,replaceHTMLCodes,html_g_tv,html_g_movie,BASE_LOGO
from public import addNolink,addDir3,addLink,lang,user_dataDir
isr='0'
lang=xbmc.getLanguage(0)
domain_s='https://'
Addon = xbmcaddon.Addon()
time_to_save=1
def get_movie_data(url):
    html=requests.get(url).json()
    return html
addonInfo = xbmcaddon.Addon().getAddonInfo
def infoDialog(message, heading=addonInfo('name'), icon='', time=3000, sound=False):
    if icon == '': icon = addonIcon()
    elif icon == 'INFO': icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING': icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR': icon = xbmcgui.NOTIFICATION_ERROR
    xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)

def manager(name, tmdb, tv_movie):
        dp = xbmcgui.DialogProgress()
        dp.create("Loading", "Please Wait", '')
        dp.update(0)
        post = {"movies": [{"ids": {"tmdb": tmdb}}]} if tv_movie == 'movie' else {"shows": [{"ids": {"tmdb": tmdb}}]}

        items = [("Add to [B]Collection[/B]", '/sync/collection')]
        items += [("Remove from [B]Collection[/B]", '/sync/collection/remove')]
        items += [("Add to [B]Watchlist[/B]", '/sync/watchlist')]
        items += [("Remove from [B]Watchlist[/B]", '/sync/watchlist/remove')]
        items += [("Add to [B]new List[/B]", '/users/me/lists/%s/items')]
        dp.update(0,'Sending Req.','')
        result = call_trakt('/users/me/lists')
        lists = [(i['name'], i['ids']['slug']) for i in result]
        lists = [lists[i//2] for i in range(len(lists)*2)]
        for i in range(0, len(lists), 2):
            lists[i] = (("Add to [B]%s[/B]" % lists[i][0]).encode('utf-8'), '/users/me/lists/%s/items' % lists[i][1])
        for i in range(1, len(lists), 2):
            lists[i] = (( "Remove from [B]%s[/B]" % lists[i][0]).encode('utf-8'), '/users/me/lists/%s/items/remove' % lists[i][1])
        items += lists
        option_list=[i[0] for i in items]
        select = xbmcgui.Dialog().select("Trakt Manager",option_list )
        dp.update(0,'Sending selection','')
        if select == -1:
            return
        elif select == 4:
            t = "Add to [B]new List[/B]"
            k = xbmc.Keyboard('', t) ; k.doModal()
            new = k.getText() if k.isConfirmed() else None
            if (new == None or new == ''): return
            result = call_trakt('/users/me/lists', data={"name": new, "privacy": "private"})
            logging.warning(result)
            slug = (result)['ids']['slug']
            try: slug = (result)['ids']['slug']
            except: return infoDialog("Trakt Manager", heading=str(name), sound=True, icon='ERROR')
            result = call_trakt(items[select][1] % slug, data=post)
        else:
            result = call_trakt(items[select][1], data=post)
        
        icon = xbmc.getInfoLabel('ListItem.Icon') if not result == None else 'ERROR'

        infoDialog(option_list[select], heading=str(name), sound=True, icon=icon)
        dp.close()
def remove_trk_resume(name,id,season,episode,type_o):
    ok=xbmcgui.Dialog().yesno("Clear %s Resume points"%('[COLOR lighblue][B]'+name+'[/B][/COLOR]'),('Are you sure there is no way back...?'))
    if ok:
        if type_o=='tv':
            type = 'episode'
            type2='show'
            multi_type = 'episodes'
        elif type_o=='movie':
            type = 'movie'
            type2='movie'
            multi_type = 'movies'
        progress = call_trakt('sync/playback/%s' % type)
        logging.warning(json.dumps(progress))
        progress = [i for i in progress if i['type'] == type]
        
        if type_o=='tv':
          logging.warning('Season:'+str(season))
          logging.warning('episode:'+str(episode))
          progress = [i for i in progress
                    if str(i[type2]['ids']['tmdb']) == str(id) and i[type]['season']==int(season) and i[type]['number']==int(episode)]
        
          logging.warning(progress)
          for i in progress:
                call_trakt('sync/playback/%s' % i['id'],is_delete=True)
        else:
            progress = [i for i in progress
                    if str(i[type2]['ids']['tmdb']) == str(id)]
            for i in progress:
                call_trakt('sync/playback/%s' % i['id'],is_delete=True)
        xbmc.executebuiltin('Container.Refresh')
def progress_trakt(url,sync=False):
        all_trk_data={}
        import _strptime
        
        aa=[]
        if  Addon.getSetting("fav_search_f_tv")=='true' and Addon.getSetting("fav_servers_en_tv")=='true' and len(Addon.getSetting("fav_servers_tv"))>0:
           fav_status='true'
        else:
            fav_status='false'
        if Addon.getSetting("dp")=='true':
                dp = xbmcgui.DialogProgress()
                dp.create("Loading", "Please Wait", '')
                dp.update(0)
        import datetime
        start_time = time.time()
        xxx=0
        ddatetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        url_g=domain_s+'api.themoviedb.org/3/genre/tv/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
     
  
        html_g=requests.get(url_g).json()
        #html_g=html_g_tv
        result = call_trakt(url)
        #logging.warning(json.dumps(result))
        items = []
        

        new_name_array=[]
        
        for item in result:
            
            try:
                num_1 = 0
                if 'seasons' in item:
                    for i in range(0, len(item['seasons'])):
                        if item['seasons'][i]['number'] > 0: num_1 += len(item['seasons'][i]['episodes'])
                    num_2 = int(item['show']['aired_episodes'])
                    if num_1 >= num_2: raise Exception()

                    season = str(item['seasons'][-1]['number'])

                    episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                    episode = sorted(episode, key=lambda x: x['number'])
                    episode = str(episode[-1]['number'])
                else:
                    season = str(item['episode']['season'])
                    episode=str(item['episode']['number'])
                   

                tvshowtitle = item['show']['title']
                if tvshowtitle == None or tvshowtitle == '': raise Exception()
                tvshowtitle = replaceHTMLCodes(tvshowtitle)

                year = item['show']['year']
                year = re.sub('[^0-9]', '', str(year))
                if int(year) > int(ddatetime.strftime('%Y')): raise Exception()

                imdb = item['show']['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'

                tmdb = item['show']['ids']['tmdb']
                if tmdb == None or tmdb == '': raise Exception()
                tmdb = re.sub('[^0-9]', '', str(tmdb))
                
               
                trakt = item['show']['ids']['trakt']
                if trakt == None or trakt == '': raise Exception()
                trakt = re.sub('[^0-9]', '', str(trakt))
                if 'last_watched_at' in item:
                    last_watched = item['last_watched_at']
                else:
                    last_watched = item['listed_at']
                
                if last_watched == None or last_watched == '': last_watched = '0'
                items.append({'imdb': imdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year, 'snum': season, 'enum': episode, '_last_watched': last_watched})
            
            except Exception as e:
               logging.warning(e)
            
            
        result = call_trakt('/users/hidden/progress_watched?limit=1000&type=show')
        result = [str(i['show']['ids']['tmdb']) for i in result]

        items_pre = [i for i in items if not i['tmdb'] in result]
        if Addon.getSetting("dp")=='false':
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        for items in items_pre:
          watched='no'
          not_yet=0
          gone=0
          season=items['snum']
          episode=items['enum']
          last_played=items['_last_watched'].replace('T',' ').replace('Z','').replace('.000','')
          url='http://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
          
          html=cache.get(get_movie_data,time_to_save,url, table='pages')
          plot=' '
          if 'The resource you requested could not be found' not in str(html):
             data=html
            
             if 'vote_average' in data:
               rating=data['vote_average']
             else:
              rating=0
             try:
                 if 'first_air_date' in data:
                   year=str(data['first_air_date'].split("-")[0])
                   order_date=data['first_air_date']
                 else:
                    if 'release_date' in data:
                      year=str(data['release_date'].split("-")[0])
                      
                      order_date=data['release_date']
                    else:
                        year=' '
                        order_date=''
             except:
                year=' '
                order_date=''
             if data['overview']==None:
               plot=' '
             else:
               plot=data['overview']
             if 'title' not in data:
               new_name=data['name']
             else:
               new_name=data['title']
             f_subs=[]
             
             original_name=data['original_name']
             id=str(data['id'])
             mode=15
             if data['poster_path']==None:
              icon=' '
             else:
               icon=data['poster_path']
             if 'backdrop_path' in data:
                 if data['backdrop_path']==None:
                  fan=' '
                 else:
                  fan=data['backdrop_path']
             else:
                fan=html['backdrop_path']
             if plot==None:
               plot=' '
             if 'http' not in fan:
               fan=domain_s+'image.tmdb.org/t/p/original/'+fan
             if 'http' not in icon:
               icon=domain_s+'image.tmdb.org/t/p/original/'+icon
             genres_list= dict([(i['id'], i['name']) for i in html_g['genres'] \
                    if i['name'] is not None])
             try:genere = u' / '.join([genres_list[x['id']] for x in data['genres']])
             except:genere=''

   
            
             trailer = "plugin://plugin.video.shadow?mode=25&url=www&id=%s" % id
             if new_name not in new_name_array:
              new_name_array.append(new_name)
              if Addon.getSetting("check_subs")=='true' or Addon.getSetting("disapear")=='true':
                  if len(f_subs)>0:
                    color='white'
                  else:
                    color='red'
                    
              else:
                 color='white'
              elapsed_time = time.time() - start_time
              if Addon.getSetting("dp")=='true':
                dp.update(int(((xxx* 100.0)/(len(html))) ), ' Please Wait '+ time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),'[COLOR'+color+']'+new_name+'[/COLOR]')
              xxx=xxx+1
              if Addon.getSetting("dp")=='true':
                if dp.iscanceled():
                    dp.close()
                    break
              if int(data['last_episode_to_air']['season_number'])>=int(season):
                if int(data['last_episode_to_air']['episode_number'])>int(episode):
                
                  episode=str(int(episode)+1)
                else:
                 if int(data['last_episode_to_air']['season_number'])>int(season):
                   season=str(int(season)+1)
                   episode='1'
                 else:
                  if (data['next_episode_to_air'])!=None:
                    episode=str(int(episode)+1)
                   
                    not_yet='1'
                  else:
                    gone=1
              else:
                    if (data['next_episode_to_air'])!=None:
                        season=str(int(season)+1)
                        episode='1'
                        not_yet='1'
                    else:
                        gone=1
              video_data={}

              if len(episode)==1:
                  episode_n="0"+episode
              else:
                   episode_n=episode
              if len(season)==1:
                  season_n="0"+season
              else:
                  season_n=season

              video_data['mediatype']='tvshow'
              video_data['OriginalTitle']=new_name
              video_data['title']=new_name+' S'+season_n+'E'+episode_n



              video_data['year']=year
              video_data['season']=season
              video_data['episode']=episode
              video_data['genre']=genere
              video_data['lastplayed']=last_played
              try:
                
                ct_date = datetime.datetime.strptime(order_date, "%Y-%m-%d").strftime("%d.%m.%Y")
              except:
                ct_date=''
              video_data['date']=ct_date
              
              if 1:#Addon.getSetting("trac_trk")=='true':
                addon='\n'+' season'+season_n+'-episode '+episode_n
              else:
                addon=''
              video_data['plot']='Aired: '+ct_date+'\nWached: '+last_played+'\n'+plot+addon
              try:
                max_ep=data['seasons'][int(season)-1]['episode_count']
              except Exception as e:
                max_ep=100
            
              if gone==0:
                  if not_yet==0:
                  
                    if episode_n=='01':
                      dates=json.dumps((0,'' ,''))
                    elif max_ep<=int(episode):
                        dates=json.dumps(('','' ,0))
                    else:
                      dates=json.dumps(('','' ,''))
                    all_trk_data[id]={}
                    all_trk_data[id]['icon']=icon
                    all_trk_data[id]['fan']=fan
                    all_trk_data[id]['plot']=last_played+'\n'+plot+addon
                    all_trk_data[id]['year']=year
                    all_trk_data[id]['original_title']=original_name
                    all_trk_data[id]['title']=new_name
                    all_trk_data[id]['season']=season
                    all_trk_data[id]['episode']=episode
                    all_trk_data[id]['eng_name']=original_name
                    all_trk_data[id]['heb_name']=new_name
                    all_trk_data[id]['type']='tv'
                    
                    
                    logging.warning('121')
                    aa.append(addDir3('[COLOR '+color+']'+new_name+'[/COLOR]'+' S'+season_n+'E'+episode_n,url,mode,icon,fan,plot+addon,data=year,original_title=original_name,id=id,rating=rating,heb_name=new_name,show_original_year=year,generes=genere,trailer=trailer,watched=watched,season=season,episode=episode,eng_name=original_name,tmdbid=id,video_info=video_data,dates=dates,fav_status=fav_status))
                  else:
                   addNolink('[COLOR red][I]'+ new_name.encode('utf8')+'[/I][/COLOR]'+' S'+season_n+'E'+episode_n, 'www',999,False,iconimage=icon,fanart=fan)
          else:
            
            logging.warning('323')
            if 'trakt' in items:
                responce=call_trakt("shows/{0}".format(items['trakt']), params={'extended': 'full'})
              
               
                addNolink('[COLOR red][I]'+ responce['title']+'[/I][/COLOR]', 'www',999,False)
        logging.warning('424')
        if Addon.getSetting("dp")=='true':
          dp.close()
        logging.warning('H7')
        xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LASTPLAYED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
        return all_trk_data
def resume_episode_list(url,sync=False):
        all_trk_data={}
        aa=[]
        
        if Addon.getSetting("dp")=='true':
                dp = xbmcgui.DialogProgress()
                dp.create("Loading", "Please Wait", '')
                dp.update(0)
        import datetime
        start_time = time.time()
        xxx=0
        ddatetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        url_g=domain_s+'api.themoviedb.org/3/genre/tv/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
     
  
        html_g=requests.get(url_g).json()
        #html_g=html_g_tv
        result = call_trakt(url)
        #logging.warning(json.dumps(result))
        items = []
       

        new_name_array=[]
        time_to_save_trk=int(Addon.getSetting("time_to_save"))
        for item in result:
           
            progress=None
          
            if 'progress' in item:
                    progress=item['progress']
                    if progress>time_to_save_trk:
                        continue
            try:
                num_1 = 0
                if 'seasons' in item:
                    for i in range(0, len(item['seasons'])):
                        if item['seasons'][i]['number'] > 0: num_1 += len(item['seasons'][i]['episodes'])
                    num_2 = int(item['show']['aired_episodes'])
                    if num_1 >= num_2: raise Exception()

                    season = str(item['seasons'][-1]['number'])

                    episode = [x for x in item['seasons'][-1]['episodes'] if 'number' in x]
                    episode = sorted(episode, key=lambda x: x['number'])
                    episode = str(episode[-1]['number'])
                else:
                    season = str(item['episode']['season'])
                    episode=str(item['episode']['number'])
                   

                tvshowtitle = item['show']['title']
                if tvshowtitle == None or tvshowtitle == '': raise Exception()
                tvshowtitle = replaceHTMLCodes(tvshowtitle)

                year = item['show']['year']
                year = re.sub('[^0-9]', '', str(year))
                if int(year) > int(ddatetime.strftime('%Y')): raise Exception()

                imdb = item['show']['ids']['imdb']
                if imdb == None or imdb == '': imdb = '0'

                tmdb = item['show']['ids']['tmdb']
                if tmdb == None or tmdb == '': raise Exception()
                tmdb = re.sub('[^0-9]', '', str(tmdb))
                
               
                trakt = item['show']['ids']['trakt']
                if trakt == None or trakt == '': raise Exception()
                trakt = re.sub('[^0-9]', '', str(trakt))
                if 'last_watched_at' in item:
                    last_watched = item['last_watched_at']
                else:
                   if 'listed_at' in item:
                    last_watched = item['listed_at']
                   else:
                    last_watched=None
                if last_watched == None or last_watched == '': last_watched = '0'
                items.append({'imdb': imdb, 'tmdb': tmdb, 'tvshowtitle': tvshowtitle, 'year': year, 'snum': season, 'enum': episode, '_last_watched': last_watched,'progress':progress})
            
            except Exception as e:
               logging.warning(item)
               logging.warning(e)
            


        items_pre = items
        if Addon.getSetting("dp")=='false':
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        for items in items_pre:
          watched='no'
          not_yet=0
          gone=0
          progress=items['progress']
          
          season=items['snum']
          episode=items['enum']
          last_played=items['_last_watched'].replace('T',' ').replace('Z','').replace('.000','')
          url='http://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
          
          html=cache.get(get_movie_data,time_to_save,url, table='pages')
          plot=' '
          if 'The resource you requested could not be found' not in str(html):
             data=html
            
             if 'vote_average' in data:
               rating=data['vote_average']
             else:
              rating=0
             if 'first_air_date' in data:
               year=str(data['first_air_date'].split("-")[0])
             else:
                if 'release_date' in data:
                  year=str(data['release_date'].split("-")[0])
                else:
                    year=' '
             if data['overview']==None:
               plot=' '
             else:
               plot=data['overview']
             if 'title' not in data:
               new_name=data['name']
             else:
               new_name=data['title']
             f_subs=[]
             
             original_name=data['original_name']
             id=str(data['id'])
             mode=15
             if data['poster_path']==None:
              icon=' '
             else:
               icon=data['poster_path']
             if 'backdrop_path' in data:
                 if data['backdrop_path']==None:
                  fan=' '
                 else:
                  fan=data['backdrop_path']
             else:
                fan=html['backdrop_path']
             if plot==None:
               plot=' '
             if 'http' not in fan:
               fan=domain_s+'image.tmdb.org/t/p/original/'+fan
             if 'http' not in icon:
               icon=domain_s+'image.tmdb.org/t/p/original/'+icon
             genres_list= dict([(i['id'], i['name']) for i in html_g['genres'] \
                    if i['name'] is not None])
             try:genere = u' / '.join([genres_list[x['id']] for x in data['genres']])
             except:genere=''

   
            
             trailer = "plugin://plugin.video.shadow?mode=25&url=tv&id=%s" % id
             if 1:
              new_name_array.append(new_name)
              
              
              color='white'
              elapsed_time = time.time() - start_time
              if Addon.getSetting("dp")=='true':
                dp.update(int(((xxx* 100.0)/(len(html))) ), ' Please Wait '+ time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),'[COLOR'+color+']'+new_name+'[/COLOR]')
              xxx=xxx+1
              if Addon.getSetting("dp")=='true':
                if dp.iscanceled():
                    dp.close()
                    break
              video_data={}

              if len(episode)==1:
                  episode_n="0"+episode
              else:
                   episode_n=episode
              if len(season)==1:
                  season_n="0"+season
              else:
                  season_n=season

              video_data['mediatype']='tvshow'
              video_data['OriginalTitle']=new_name
              video_data['title']=new_name+' S'+season_n+'E'+episode_n



              video_data['year']=year
              video_data['season']=season
              video_data['episode']=episode
              video_data['genre']=genere
              video_data['lastplayed']=last_played
              
              
              if 1:#Addon.getSetting("trac_trk")=='true':
                addon='\n'+' season'+season_n+'-episode '+episode_n
              
              video_data['plot']=str(progress)+'%\n'+plot+addon
              
            
              if gone==0 or sync==True:
                  if not_yet==0:
                  
                    if episode_n=='01':
                      dates=json.dumps((0,'' ,''))
                    
                    else:
                      dates=json.dumps(('','' ,''))
                    all_trk_data[id]={}
                    all_trk_data[id]['icon']=icon
                    all_trk_data[id]['fan']=fan
                    all_trk_data[id]['plot']=str(progress)+'%\n'+plot+addon
                    all_trk_data[id]['year']=year
                    all_trk_data[id]['original_title']=original_name
                    all_trk_data[id]['title']=new_name
                    all_trk_data[id]['season']=season
                    all_trk_data[id]['episode']=episode
                    all_trk_data[id]['eng_name']=original_name
                    all_trk_data[id]['heb_name']=new_name
                    all_trk_data[id]['type']='tv'
                    all_w={}
                    mark_time=False
                    if progress!=None:
                      
                          all_w[id]={}
                          all_w[id]['precentage']=str(progress)
                          mark_time=True
                    
                    aa.append(addDir3('[COLOR '+color+']'+new_name+'[/COLOR]'+' S'+season_n+'E'+episode_n,url,mode,icon,fan,plot+addon,data=year,original_title=original_name,id=id,rating=rating,heb_name=new_name,show_original_year=year,generes=genere,trailer=trailer,watched=watched,season=season,episode=episode,eng_name=original_name,tmdbid=id,video_info=video_data,dates=dates,mark_time=mark_time,all_w=all_w))
                  else:
                    all_trk_data[id]={}
                    all_trk_data[id]['icon']=icon
                    all_trk_data[id]['fan']=fan
                    all_trk_data[id]['plot']=last_played+'\n'+plot+addon
                    all_trk_data[id]['year']=year
                    all_trk_data[id]['original_title']=original_name
                    all_trk_data[id]['title']=new_name
                    all_trk_data[id]['season']=season
                    all_trk_data[id]['episode']=episode
                    all_trk_data[id]['eng_name']=original_name
                    all_trk_data[id]['heb_name']=new_name
                    all_trk_data[id]['type']='tv'
                    addNolink('[COLOR red][I]'+ new_name.encode('utf8')+'[/I][/COLOR]'+' S'+season_n+'E'+episode_n, 'www',999,False,iconimage=icon,fanart=fan)
          else:
            
            logging.warning('323')
            if 'trakt' in items:
                responce=call_trakt("shows/{0}".format(items['trakt']), params={'extended': 'full'})
              
               
                addNolink('[COLOR red][I]'+ responce['title']+'[/I][/COLOR]', 'www',999,False)
        logging.warning('424')
        if Addon.getSetting("dp")=='true':
          dp.close()
        logging.warning('H7')
        xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LASTPLAYED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
        
        return all_trk_data
def nextep_airdate_format():
    date_format = '0'
    if date_format == '0': return '%d-%m-%Y'
    elif date_format == '1': return '%Y-%m-%d'
    elif date_format == '2': return '%m-%d-%Y'
    else: return '%Y-%m-%d'
def make_day(date, use_words=True):
    from datetime import timedelta
    import datetime
    import time
    date=datetime.datetime.strptime(unicode(date), "%Y-%m-%dT%H:%M:%S.%fZ")
    from datetime import datetime
    today = datetime.utcnow()
    day_diff = (date - today).days
    date_format = nextep_airdate_format()
    try: day = date.strftime(date_format)
    except ValueError: day = date.strftime('%Y-%m-%d')
    if use_words:
        if day_diff == -1:
            day = '[COLOR lightblue]YESTERDAY[/COLOR]'
        elif day_diff == 0:
            day = '[COLOR khaki]TODAY[/COLOR]'
        elif day_diff == 1:
            day = '[COLOR yellow]TOMORROW[/COLOR]'
        elif 1 < day_diff < 7:
            day = date.strftime('%A').upper()
    return ' ['+day+'] '
    

def get_trk_data(url):
        if 'calendars' in url:
            import _strptime
            import datetime
        all_trk_data={}
        aa=[]
        auth_needed=True
        if '$$$noaut' in url:
            url=url.replace('$$$noaut','')
            auth_needed=False
        o_url=url
        if '%s' in url :
            all_o=['all','yearly','monthly','weekly']
            all_n=['All times','Yearly','Monthly','Weekly']
            ret = xbmcgui.Dialog().select("Choose", all_n)
            if ret!=-1:
                url=url%all_o[ret]
            else:
                return 0
            auth_needed=False
        # time_to_save=int(Addon.getSetting("save_time"))
        xxx=0
        if Addon.getSetting("dp")=='true':
                    dp = xbmcgui.DialogProgress()
                    dp.create("Loading ", "Please Wait", '')
                    dp.update(0)
        url_g_m=domain_s+'api.themoviedb.org/3/genre/movie/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
                     
        
        url_g_tv=domain_s+'api.themoviedb.org/3/genre/tv/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
        #html_g_tv=requests.get(url_g_tv).json()
        #html_g_m=requests.get(url_g_m).json()
        #html_g_tv=html_g_tv
        
        html_g_m=html_g_movie
        start_time = time.time()
        src="tmdb" 
        if 'trending' in url or auth_needed==False:
            with_auth=False
        else:
            with_auth=True
        try:
            i = (call_trakt('/users/me/watched/movies',with_auth=with_auth))
        except:
            i=[]
        
        all_movie_w=[]
        for ids in i:
          all_movie_w.append(str(ids['movie']['ids']['tmdb']))
        '''
        i = (call_trakt('/users/me/watched/shows?extended=full'))
        all_tv_w={}
        for ids in i:
         all_tv_w[str(ids['show']['ids']['tmdb'])]=[]
         for seasons in ids['seasons']:
          for ep in seasons['episodes']:
            all_tv_w[str(ids['show']['ids']['tmdb'])].append(str(seasons['number'])+'x'+str(ep['number']))
        '''
        type_to_show='all'
        if '^^^^^^^^' in url:
            data_in=url.split('$$$$$$$$$$$')
            user = data_in[0]
            slug = data_in[1].split('^^^^^^^^')[0]
            data_in2=url.split('^^^^^^^^')
            type_to_show=data_in2[1]
            selected={'slug':data_in[1],'user':data_in[0]}

            responce=call_trakt("/users/{0}/lists/{1}/items".format(user, slug))
        elif '$$$$$$$$$$$' in url:
            data_in=url.split('$$$$$$$$$$$')
            user = data_in[0]
            slug = data_in[1]
            selected={'slug':data_in[1],'user':data_in[0]}

            responce=call_trakt("/users/{0}/lists/{1}/items".format(user, slug))
        else:
           responce=call_trakt(url,with_auth=with_auth)
        
        new_name_array=[]
        if Addon.getSetting("dp")=='false':
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        for items in responce:
         
          progress=None
          revenue=None
          if 'revenue' in items:
            revenue=items['revenue']
          if 'progress' in items:
                progress=items['progress']
          
          if 'show' in items:
             slug = 'tv'
             html_g=html_g_tv
          else:
            slug = 'movies'
            html_g=html_g_m
          if slug=='movies':
            url='http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['movie']['ids']['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
            s_id=items['movie']['ids']['tmdb']          
          else:
            url='http://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['show']['ids']['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
            s_id=items['show']['ids']['tmdb']
          date_mark=''
          season='%20'
          episode='%20'
          saved_date=''
          if 'first_aired' in items :
           if 'calendars' in o_url:
            saved_date=items['first_aired']
            date_mark=make_day(items['first_aired'])
            season=str(items['episode']['season'])
            episode=str(items['episode']['number'])
          html=cache.get(get_movie_data,72,url, table='pages')
          if 'The resource you requested could not be found' not in str(html):
             data=html
             if 'runtime' in data:
                runtime=data['runtime']
             else:
                runtime=0
             if 'overview' not in data:
                continue
             if 'vote_average' in data:
               rating=data['vote_average']
             else:
              rating=0
             
             if 'first_air_date' in data :
               
               if data['first_air_date']==None:
                    year=' '
               else:
                   year=str(data['first_air_date'].split("-")[0])
             else:
                 if 'release_date' in data:
                    if data['release_date']==None:
                        year=' '
                    else:
                        year=str(data['release_date'].split("-")[0])
                 else:
                    year=' '
        
             if data['overview']==None:
               plot=' '
             else:
               plot=data['overview']
             if 'title' not in data:
               new_name=data['name']
             else:
               new_name=data['title']
             f_subs=[]
             if slug=='movies':
               if type_to_show=='tv':
                  continue
               original_name=data['original_title']
               mode=15
               
               id=str(data['id'])
               if Addon.getSetting("check_subs")=='true' or Addon.getSetting("disapear")=='true':
                 f_subs=cache.get(get_subs,9999,'movie',original_name,'0','0',id,year,True, table='pages')
               
               
             else:
               if type_to_show=='movie':
                  continue
               original_name=data['original_name']
               id=str(data['id'])
               mode=16
             if data['poster_path']==None:
              icon=' '
             else:
               icon=data['poster_path']
             if 'backdrop_path' in data:
                 if data['backdrop_path']==None:
                  fan=' '
                 else:
                  fan=data['backdrop_path']
             else:
                fan=html['backdrop_path']
             if plot==None:
               plot=' '
             if 'http' not in fan:
               fan=domain_s+'image.tmdb.org/t/p/original/'+fan
             if 'http' not in icon:
               icon=domain_s+'image.tmdb.org/t/p/original/'+icon
             genres_list= dict([(i['id'], i['name']) for i in html_g['genres'] \
                    if i['name'] is not None])
             try:genere = u' / '.join([genres_list[x['id']] for x in data['genres']])
             except:genere=''

   
            
             trailer = "plugin://plugin.video.shadow?mode=25&url=%s&id=%s" %(slug, s_id)
             if new_name not in new_name_array:
              if 'calendars' not in o_url:
                new_name_array.append(new_name)
              if Addon.getSetting("check_subs")=='true' or Addon.getSetting("disapear")=='true':
                  if len(f_subs)>0:
                    color='white'
                  else:
                    color='red'
                    
              else:
                 color='white'
              elapsed_time = time.time() - start_time
              if Addon.getSetting("dp")=='true':
                dp.update(int(((xxx* 100.0)/(len(responce))) ), ' Please Wait '+ time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),'[COLOR'+color+']'+new_name+'[/COLOR]',str(xxx)+'/'+str(len(responce)))
              xxx=xxx+1
              if Addon.getSetting("dp")=='true':
                if dp.iscanceled():
                    dp.close()
                    break
              watched='no'
              if id in all_movie_w:
                watched='yes'
              '''
              if id in all_tv_w:
                 if season+'x'+episode in all_tv_w[id]:
                  watched='yes'
              '''
              if slug=='movies':
                    fav_search_f=Addon.getSetting("fav_search_f")
                    fav_servers_en=Addon.getSetting("fav_servers_en")
                    fav_servers=Addon.getSetting("fav_servers")
                   
                    google_server= Addon.getSetting("google_server")
                    rapid_server=Addon.getSetting("rapid_server")
                    direct_server=Addon.getSetting("direct_server")
                    heb_server=Addon.getSetting("heb_server")
              else:
                    fav_search_f=Addon.getSetting("fav_search_f_tv")
                    fav_servers_en=Addon.getSetting("fav_servers_en_tv")
                    fav_servers=Addon.getSetting("fav_servers_tv")
                    google_server= Addon.getSetting("google_server_tv")
                    rapid_server=Addon.getSetting("rapid_server_tv")
                    direct_server=Addon.getSetting("direct_server_tv")
                    heb_server=Addon.getSetting("heb_server_tv")
        
   
              if  fav_search_f=='true' and fav_servers_en=='true' and (len(fav_servers)>0 or heb_server=='true' or google_server=='true' or rapid_server=='true' or direct_server=='true'):
                    fav_status='true'
              else:
                    fav_status='false'
              if revenue:
                plot='[COLOR lightblue][I][B]Revenue: '+str(revenue)+" $[/I][/B][/COLOR]\n"+plot
              if 'T' in saved_date:
                plot=saved_date.split('T')[0]+'\n'+plot
              all_trk_data[id]={}
              all_trk_data[id]['icon']=icon
              all_trk_data[id]['fan']=fan
              all_trk_data[id]['plot']=plot
              all_trk_data[id]['year']=year
              all_trk_data[id]['original_title']=original_name
              all_trk_data[id]['title']=new_name
              all_trk_data[id]['season']=season
              all_trk_data[id]['episode']=episode
              all_trk_data[id]['eng_name']=original_name
              all_trk_data[id]['heb_name']=new_name
              all_trk_data[id]['type']='movie'
              all_w={}
              mark_time=False
              if progress!=None and runtime>0:
              
                  all_w[id]={}
                  all_w[id]['resume']=str((progress*runtime*60)/100)
                  all_w[id]['totaltime']=str(runtime*60)
                  mark_time=True
              ct_date=''
              added_se=''
              if 'calendars' in o_url:
                  mode=15
                  if len(episode)==1:
                      episode_n="0"+episode
                  else:
                       episode_n=episode
                  if len(season)==1:
                      season_n="0"+season
                  else:
                      season_n=season
                  try:
                    ct_date = datetime.datetime.strptime(saved_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d.%m.%Y")
                  except:
                    ct_date=''
                  added_se=' S%sE%s '%(season_n,episode_n)
              aa.append(addDir3('[COLOR '+color+']'+date_mark+added_se+new_name+'[/COLOR]',url,mode,icon,fan,plot,season=season,episode=episode,data=year,original_title=original_name,id=id,rating=rating,heb_name=new_name,show_original_year=year,isr=isr,generes=genere,trailer=trailer,watched=watched,fav_status=fav_status,all_w=all_w,mark_time=mark_time,ct_date=ct_date))
          else:
            
            if slug=='movies':
                responce2=call_trakt("movies/{0}".format(items['movie']['ids']['trakt']), params={'extended': 'full'},with_auth=with_auth)
            else:
                responce2=call_trakt("shows/{0}".format(items['show']['ids']['trakt']), params={'extended': 'full'},with_auth=with_auth)
           
            
            addNolink('[COLOR red][I]'+ responce2['title']+'-Not exists on TMDB[/I][/COLOR]', 'www',999,False)
            
        if Addon.getSetting("dp")=='true':
          dp.close()
        logging.warning('H8')
        if 'page' in o_url:
            regex='page=(.+?)$'
            match=re.compile(regex).findall(o_url)
            aa.append(addDir3('[COLOR aqua][I]Next Page[/I][/COLOR]',o_url.split('page=')[0]+'page='+str(int(match[0])+1),117,BASE_LOGO+'next.png','https://cdn4.iconfinder.com/data/icons/arrows-1-6/48/1-512.png','Next',show_original_year='999',data='999',collect_all=True))
        
        xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
        if 'trending' not in o_url:
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
        if 'calendars' in o_url:
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
        return all_trk_data
def get_simple_trk_data(url):
        o_url=url
    
        all_trk_data={}
        aa=[]
        # time_to_save=int(Addon.getSetting("save_time"))
        xxx=0
        auth_needed=True
        if '$$$noaut' in url:
            url=url.replace('$$$noaut','')
            auth_needed=False
            
        if Addon.getSetting("dp")=='true':
                    dp = xbmcgui.DialogProgress()
                    dp.create("Loading ", "Please Wait", '')
                    dp.update(0)
        url_g_m=domain_s+'api.themoviedb.org/3/genre/movie/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
                     
        
        url_g_tv=domain_s+'api.themoviedb.org/3/genre/tv/list?api_key=34142515d9d23817496eeb4ff1d223d0&language='+lang
        #html_g_tv=requests.get(url_g_tv).json()
        #html_g_m=requests.get(url_g_m).json()
        #html_g_tv=html_g_tv
        
        html_g_m=html_g_movie
        start_time = time.time()
        src="tmdb" 
        with_auth=False
        if 'recommendations' in o_url:
            with_auth=True
        
        
        
     
         
        
        responce=call_trakt(url,with_auth=with_auth)
        
        new_name_array=[]
        o_url=url
        if Addon.getSetting("dp")=='false':
            xbmc.executebuiltin("Dialog.Close(busydialog)")
        for items in responce:
          progress=None
          
          if 'progress' in items:
                progress=items['progress']
          
          if 'show' in items or 'shows' in o_url:
             slug = 'tv'
             html_g=html_g_tv
          else:
            slug = 'movies'
            html_g=html_g_m
          
          if slug=='movies':
            url='http://api.themoviedb.org/3/movie/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['ids']['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
            s_id=items['ids']['tmdb']          
          else:
            url='http://api.themoviedb.org/3/tv/%s?api_key=%s&language=%s&append_to_response=external_ids'%(items['ids']['tmdb'],'653bb8af90162bd98fc7ee32bcbbfb3d',lang)
            s_id=items['ids']['tmdb']
          
          html=cache.get(get_movie_data,72,url, table='pages')
          if 'The resource you requested could not be found' not in str(html):
             data=html
             if 'runtime' in data:
                runtime=data['runtime']
             else:
                runtime=0
             if 'overview' not in data:
                continue
             if 'vote_average' in data:
               rating=data['vote_average']
             else:
              rating=0
             if 'first_air_date' in data :
               if data['first_air_date']==None:
                    year=' '
               else:
                   year=str(data['first_air_date'].split("-")[0])
             else:
                 if 'release_date' in data:
                    if data['release_date']==None:
                        year=' '
                    else:
                        year=str(data['release_date'].split("-")[0])
                 else:
                    year=' '
        
             if data['overview']==None:
               plot=' '
             else:
               plot=data['overview']
             if 'title' not in data:
               new_name=data['name']
             else:
               new_name=data['title']
             f_subs=[]
             if slug=='movies':
               original_name=data['original_title']
               mode=15
               
               id=str(data['id'])
               if Addon.getSetting("check_subs")=='true' or Addon.getSetting("disapear")=='true':
                 f_subs=cache.get(get_subs,9999,'movie',original_name,'0','0',id,year,True, table='pages')
               
               
             else:
               original_name=data['original_name']
               id=str(data['id'])
               mode=16
             if data['poster_path']==None:
              icon=' '
             else:
               icon=data['poster_path']
             if 'backdrop_path' in data:
                 if data['backdrop_path']==None:
                  fan=' '
                 else:
                  fan=data['backdrop_path']
             else:
                fan=html['backdrop_path']
             if plot==None:
               plot=' '
             if 'http' not in fan:
               fan=domain_s+'image.tmdb.org/t/p/original/'+fan
             if 'http' not in icon:
               icon=domain_s+'image.tmdb.org/t/p/original/'+icon
             genres_list= dict([(i['id'], i['name']) for i in html_g['genres'] \
                    if i['name'] is not None])
             try:genere = u' / '.join([genres_list[x['id']] for x in data['genres']])
             except:genere=''

   
            
             trailer = "plugin://plugin.video.shadow?mode=25&url=%s&id=%s" %(slug, s_id)
             if new_name not in new_name_array:
              new_name_array.append(new_name)
              if Addon.getSetting("check_subs")=='true' or Addon.getSetting("disapear")=='true':
                  if len(f_subs)>0:
                    color='white'
                  else:
                    color='red'
                    
              else:
                 color='white'
              elapsed_time = time.time() - start_time
              if Addon.getSetting("dp")=='true':
                dp.update(int(((xxx* 100.0)/(len(html))) ), ' Please Wait '+ time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),'[COLOR'+color+']'+new_name+'[/COLOR]',str(xxx)+'/'+str(len(responce)))
              xxx=xxx+1
              if Addon.getSetting("dp")=='true':
                if dp.iscanceled():
                    dp.close()
                    break
              watched='no'
              
              if slug=='movies':
                    fav_search_f=Addon.getSetting("fav_search_f")
                    fav_servers_en=Addon.getSetting("fav_servers_en")
                    fav_servers=Addon.getSetting("fav_servers")
                   
                    google_server= Addon.getSetting("google_server")
                    rapid_server=Addon.getSetting("rapid_server")
                    direct_server=Addon.getSetting("direct_server")
                    heb_server=Addon.getSetting("heb_server")
              else:
                    fav_search_f=Addon.getSetting("fav_search_f_tv")
                    fav_servers_en=Addon.getSetting("fav_servers_en_tv")
                    fav_servers=Addon.getSetting("fav_servers_tv")
                    google_server= Addon.getSetting("google_server_tv")
                    rapid_server=Addon.getSetting("rapid_server_tv")
                    direct_server=Addon.getSetting("direct_server_tv")
                    heb_server=Addon.getSetting("heb_server_tv")
        
   
              if  fav_search_f=='true' and fav_servers_en=='true' and (len(fav_servers)>0 or heb_server=='true' or google_server=='true' or rapid_server=='true' or direct_server=='true'):
                    fav_status='true'
              else:
                    fav_status='false'
             
              all_trk_data[id]={}
              all_trk_data[id]['icon']=icon
              all_trk_data[id]['fan']=fan
              all_trk_data[id]['plot']=plot
              all_trk_data[id]['year']=year
              all_trk_data[id]['original_title']=original_name
              all_trk_data[id]['title']=new_name
              all_trk_data[id]['season']='%20'
              all_trk_data[id]['episode']='%20'
              all_trk_data[id]['eng_name']=original_name
              all_trk_data[id]['heb_name']=new_name
              all_trk_data[id]['type']='movie'
              all_w={}
              mark_time=False
              if progress!=None and runtime>0:
              
                  all_w[id]={}
                  all_w[id]['resume']=str((progress*runtime*60)/100)
                  all_w[id]['totaltime']=str(runtime*60)
                  mark_time=True
                  
                  
              aa.append(addDir3('[COLOR '+color+']'+new_name+'[/COLOR]',url,mode,icon,fan,plot,data=year,original_title=original_name,id=id,rating=rating,heb_name=new_name,show_original_year=year,isr=isr,generes=genere,trailer=trailer,watched=watched,fav_status=fav_status,all_w=all_w,mark_time=mark_time))
          else:
            
            if slug=='movies':
                responce2=call_trakt("movies/{0}".format(items['movie']['ids']['trakt']), params={'extended': 'full'},with_auth=with_auth)
            else:
                responce2=call_trakt("shows/{0}".format(items['show']['ids']['trakt']), params={'extended': 'full'},with_auth=with_auth)
           
           
            addNolink('[COLOR red][I]'+ responce2['title']+'[/I][/COLOR]', 'www',999,False)
            
        if Addon.getSetting("dp")=='true':
          dp.close()

        if 'page' in o_url:
            regex='page=(.+?)$'
            match=re.compile(regex).findall(o_url)
            aa.append(addDir3('[COLOR aqua][I]Next Page[/I][/COLOR]',o_url.split('page=')[0]+'page='+str(int(match[0])+1),166,BASE_LOGO+'next.png','https://cdn4.iconfinder.com/data/icons/arrows-1-6/48/1-512.png','Next',show_original_year='999',data='999',collect_all=True))
           
        xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
        if 'trending' not in o_url:
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

            xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
        return all_trk_data
def get_one_trk(color,name,url_o,url,icon,fanart,data_ep,plot,year,original_title,id,season,episode,eng_name,show_original_year,heb_name,isr,dates,xxx,image):
          global all_data_imdb
          import _strptime
          data_ep=''
          dates=' '
          fanart=image
          url=domain_s+'api.themoviedb.org/3/tv/%s/season/%s?api_key=34142515d9d23817496eeb4ff1d223d0&language=%s'%(id,season,lang)
         
          html=requests.get(url).json()
          next=''
          ep=0
          f_episode=0
          catch=0
          counter=0
          if 'episodes' in html:
              for items in html['episodes']:
                if 'air_date' in items:
                   try:
                       datea=items['air_date']+'\n'
                       
                       a=(time.strptime(items['air_date'], '%Y-%m-%d'))
                       b=time.strptime(str(time.strftime('%Y-%m-%d')), '%Y-%m-%d')
                      
                   
                       if a>b:
                         if catch==0:
                           f_episode=counter
                           
                           catch=1
                       counter=counter+1
                       
                   except:
                         ep=0
          else:
             ep=0
          episode_fixed=int(episode)-1
          try:
              plot=html['episodes'][int(episode_fixed)]['overview']
          
              ep=len(html['episodes'])
              if (html['episodes'][int(episode_fixed)]['still_path'])==None:
                fanart=image
              else:
                fanart=domain_s+'image.tmdb.org/t/p/original/'+html['episodes'][int(episode_fixed)]['still_path']
              if f_episode==0:
                f_episode=ep
              data_ep='[COLOR aqua]'+'season '+season+'-episode '+episode+ '[/COLOR]\n[COLOR yellow] out of  ' +str(f_episode)  +' episodes for this season [/COLOR]\n' 
              if int(episode)>1:
                
                prev_ep=time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)-1]['air_date'], '%Y-%m-%d'))) 
              else:
                prev_ep=0

          

                      
              if int(episode)<ep:

                if (int(episode)+1)>=f_episode:
                  color_ep='magenta'
                  next_ep='[COLOR %s]'%color_ep+time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)+1]['air_date'], '%Y-%m-%d'))) +'[/COLOR]'
                else:
                  
                  next_ep=time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)+1]['air_date'], '%Y-%m-%d'))) 
              else:
                next_ep=0
              dates=((prev_ep,time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)]['air_date'], '%Y-%m-%d'))) ,next_ep))
              if int(episode)<int(f_episode):
               color='yellow'
              else:
               color='white'
               h2=requests.get('https://api.themoviedb.org/3/tv/%s?api_key=34142515d9d23817496eeb4ff1d223d0&language=en-US'%id).json()
               last_s_to_air=int(h2['last_episode_to_air']['season_number'])
               last_e_to_air=int(h2['last_episode_to_air']['episode_number'])
              
               if int(season)<last_s_to_air:
        
                 color='lightblue'
            
               if h2['status']=='Ended' or h2['status']=='Canceled':
                color='peru'
               
               
               if h2['next_episode_to_air']!=None:
                 
                 if 'air_date' in h2['next_episode_to_air']:
                  
                  a=(time.strptime(h2['next_episode_to_air']['air_date'], '%Y-%m-%d'))
                  next=time.strftime( "%d-%m-%Y",a)
                  
               else:
                  next=''
                 
          except Exception as e:
              logging.warning('Error :'+ heb_name)
              logging.warning('Error :'+ str(e))
              plot=' '
              color='green'
              if f_episode==0:
                f_episode=ep
              data_ep='[COLOR aqua]'+'season '+season+'-episode '+episode+ '[/COLOR]\n[COLOR yellow] out of  ' +str(f_episode)  +' episodes for this season [/COLOR]\n' 
              dates=' '
              fanart=image
          try:
            f_name=urllib.unquote_plus(heb_name.encode('utf8'))
     
          except:
            f_name=name
          if (heb_name)=='':
            f_name=name
          if color=='peru':
            add_p='[COLOR peru][B]Ended or canceled[/B][/COLOR]'+'\n'
          else:
            add_p=''
          add_n=''
          if color=='white' and url_o=='tv' :
              if next !='':
                add_n='[COLOR tomato][I]Next episode at ' +next+'[/I][/COLOR]\n'
              else:
                add_n='[COLOR tomato][I]Next episode at ' +' Unknown '+'[/I][/COLOR]\n'
                next='???'
          
          added_txt=' [COLOR khaki][I]%sx%s[/I][/COLOR] '%(season,episode)
          all_data_imdb.append((color,f_name+' '+added_txt+' '+next,url,icon,fanart,add_p,data_ep,add_n,plot,year,original_title,id,season,episode,eng_name,show_original_year,heb_name,isr,dates,xxx))
          return data_ep,dates,fanart,color,next
def get_Series_trk_data(url_o,match):
        import _strptime
        cacheFile_trk = os.path.join(user_dataDir, 'cache_play_trk.db')
        dbcon_trk2 = database.connect(cacheFile_trk)
        dbcur_trk2  = dbcon_trk2.cursor()
        dbcur_trk2.execute("CREATE TABLE IF NOT EXISTS %s ( ""data_ep TEXT, ""dates TEXT, ""fanart TEXT,""color TEXT,""id TEXT,""season TEXT,""episode TEXT, ""next TEXT,""plot TEXT);" % 'AllData4')
        dbcon_trk2.commit()
        dbcur_trk2.execute("DELETE FROM AllData4")
        logging.warning('Updating sh')
        image=' '
        for item in match:
          next=''
          name,url,icon,image,plot,year,original_title,season,episode,id,eng_name,show_original_year,heb_name,isr,tv_movie=item
          #name,id,season,episode=item
          data_ep=''
          dates=' '
          fanart=image
          url=domain_s+'api.themoviedb.org/3/tv/%s/season/%s?api_key=34142515d9d23817496eeb4ff1d223d0&language=%s'%(id,season,lang)
         
          html=requests.get(url).json()
          if 'status_message' in html:
            if html['status_message']!='The resource you requested could not be found.':
                xbmc.sleep(10000)
                html=requests.get(url).json()
            
          ep=0
          f_episode=0
          catch=0
          counter=0
          if 'episodes' in html:
              for items in html['episodes']:
                if 'air_date' in items:
                   try:
                       datea=items['air_date']+'\n'
                       
                       a=(time.strptime(items['air_date'], '%Y-%m-%d'))
                       b=time.strptime(str(time.strftime('%Y-%m-%d')), '%Y-%m-%d')
                      
                   
                       if a>b:
                         if catch==0:
                           f_episode=counter
                           
                           catch=1
                       counter=counter+1
                       
                   except:
                         ep=0
          else:
             ep=0
          episode_fixed=int(episode)-1
          try:
              try:
                plot=html['episodes'][int(episode_fixed)]['overview']
              except:
                logging.warning(name.decode('utf-8'))
                if 'episodes' not in html:
                    logging.warning(html)
                    
                
                logging.warning(episode_fixed)
                
                plot=''
                pass
              
          
              ep=len(html['episodes'])
              if (html['episodes'][int(episode_fixed)]['still_path'])==None:
                fanart=image
              else:
                fanart=domain_s+'image.tmdb.org/t/p/original/'+html['episodes'][int(episode_fixed)]['still_path']
              if f_episode==0:
                f_episode=ep
              data_ep='[COLOR aqua]'+'season '+season+'-episode '+episode+ '[/COLOR]\n[COLOR yellow] out of  ' +str(f_episode)  +' Episodes per season [/COLOR]\n' 
              if int(episode)>1:
                
                prev_ep=time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)-1]['air_date'], '%Y-%m-%d'))) 
              else:
                prev_ep=0

          

              try:
                  if int(episode)<ep:
                    
                    if (int(episode)+1)>=f_episode:
                      color_ep='magenta'
                      next_ep='[COLOR %s]'%color_ep+time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)+1]['air_date'], '%Y-%m-%d'))) +'[/COLOR]'
                    else:
                      
                      next_ep=time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)+1]['air_date'], '%Y-%m-%d'))) 
                  else:
                    next_ep=0
              except:
                next_ep=0
              dates=((prev_ep,time.strftime( "%d-%m-%Y",(time.strptime(html['episodes'][int(episode_fixed)]['air_date'], '%Y-%m-%d'))) ,next_ep))
              if int(episode)<int(f_episode):
               color='yellow'
              else:
               color='white'
               h2=requests.get('https://api.themoviedb.org/3/tv/%s?api_key=34142515d9d23817496eeb4ff1d223d0&language=en-US'%id).json()
               last_s_to_air=int(h2['last_episode_to_air']['season_number'])
               last_e_to_air=int(h2['last_episode_to_air']['episode_number'])
              
               if int(season)<last_s_to_air:
                 logging.warning('bigger')
                 color='lightblue'
               if h2['status']=='Ended' or h2['status']=='Canceled':
                color='peru'
                
               if h2['next_episode_to_air']!=None:
                 if 'air_date' in h2['next_episode_to_air']:
                    a=(time.strptime(h2['next_episode_to_air']['air_date'], '%Y-%m-%d'))
                    next=time.strftime( "%d-%m-%Y",a)
               else:
                  next=''
          
          except Exception as e:
              import linecache
              exc_type, exc_obj, tb = sys.exc_info()
              f = tb.tb_frame
              lineno = tb.tb_lineno
              filename = f.f_code.co_filename
              linecache.checkcache(filename)
              line = linecache.getline(filename, lineno, f.f_globals)
              error='''\
              line no:%s,
              line:%s,
              error:%s,
              url:%s,
              ep_no:%s,
              '''%(str(lineno),line,str(e),url,episode_fixed)
              
              
              
              
              logging.warning(error)
              logging.warning('BAD Series Tracker')
              plot=' '
              color='green'
              if f_episode==0:
                f_episode=ep
              data_ep='[COLOR aqua]'+'season '+season+'-episode '+episode+ '[/COLOR]\n[COLOR yellow] out of  ' +str(f_episode)  +' Episodes per season [/COLOR]\n' 
              dates=' '
              fanart=image
          
          dbcon_trk2.execute("INSERT INTO AllData4 Values ('%s', '%s', '%s', '%s','%s', '%s', '%s','%s','%s');" % (data_ep.replace("'","%27"),json.dumps(dates),fanart.replace("'","%27"),color,id,season,episode,next,plot.replace("'","%27")))
        dbcon_trk2.commit()
        dbcon_trk2.close()
        logging.warning('TRD SUCE')
        return 0
def trakt_liked(url,iconImage,fanart):
    responce=call_trakt(url)
    aa=[]
    
    
    for items in responce:
       
        url=items['list']['user']['username']+'$$$$$$$$$$$'+items['list']['ids']['slug']
        aa.append(addDir3(items['list']['name'],url,117,iconImage,fanart,items['list']['description']))
       
        
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
def get_simple_trakt(url):
    
    trakt_lists=call_trakt(url,with_auth=False)
   
    #trakt_lists=call_trakt('users/me/collection/shows')
    aa=[]
    my_lists = []
    
    for list in trakt_lists:
        list=list['list']
        my_lists.append({
            'name': list["name"],
            'user': list["user"]["username"],
            'slug': list["ids"]["slug"]
        })

    for item in my_lists:
       
        user = item['user']
        slug = item['slug']
        url=user+'$$$$$$$$$$$'+slug
        aa.append(addDir3(item['name']+' ['+user+']',url+"$$$noaut",117,BASE_LOGO+'trakt.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg',item['name']))
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))
def get_trakt(url):
    o_url=url
    trakt_lists=call_trakt("users/me/lists")
    
    #trakt_lists=call_trakt('users/me/collection/shows')
    aa=[]
    my_lists = []
    
    for list in trakt_lists:
        my_lists.append({
            'name': list["name"],
            'user': list["user"]["username"],
            'slug': list["ids"]["slug"]
        })

    for item in my_lists:
        user = item['user']
        slug = item['slug']
        url=user+'$$$$$$$$$$$'+slug+'^^^^^^^^'+o_url
        aa.append(addDir3(item['name'] ,url,117,' ',' ',item['name']))
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),aa,len(aa))