import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'
import { useRouter } from 'vue-router'

export const useCounterStore = defineStore('counter', () => {
  const API_URL = import.meta.env.VITE_APP_API_URL
  const userKey=ref(null)
  const token = ref(null)
  const router = useRouter()
  const currentUser = ref(null)
  const userLocation = ref({
    latitude: null,
    longitude: null
  })

  const signUp = function (payload) {
    const { username, password1, password2, email, name } = payload

    axios({
      method: 'post',
      url: `${API_URL}/api/auth/registration/`, // URL 수정
      data: {
        username, 
        password1, 
        password2,
        email,
        name
      }
    })
      .then((res) => {
        console.log('회원가입 성공:', res.data)
        alert('회원가입이 완료되었습니다. 로그인해주세요.')
        router.push({ name: 'login' })
      })
      .catch((err) => {
        console.log('회원가입 실패:', err.response?.data)
        // 에러 메시지 표시
        if (err.response?.data) {
          const errorMessages = []
          Object.keys(err.response.data).forEach(key => {
            errorMessages.push(`${key}: ${err.response.data[key].join(' ')}`)
          })
          alert(errorMessages.join('\n'))
        } else {
          alert('회원가입 중 오류가 발생했습니다.')
        }
      })
  }

  const logIn = function (payload) {
    const { username, password } = payload

    // 위치 정보 가져오기
    const getCurrentPosition = () => {
      return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
          reject(new Error('Geolocation is not supported by this browser.'))
        }
        
        navigator.geolocation.getCurrentPosition(
          position => resolve(position),
          error => reject(error),
          { enableHighAccuracy: true }
        )
      })
    }

    axios({
      method: 'post',
      url: `${API_URL}/api/auth/login/`,
      data: {
        username, password
      }
    })
      .then(async (res) => {
        // 토큰 저장
        token.value = res.data.key
        
        try {
          // 위치 정보 가져오기
          const position = await getCurrentPosition()
          // store에 위치 정보 저장
          userLocation.value = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          }
        } catch (error) {
          console.error('위치 정보 가져오기 실패:', error)
        }

        // 사용자 정보 요청
        return axios({
          method: 'get',
          url: `${API_URL}/api/auth/user/`,
          headers: {
            Authorization: `Token ${res.data.key}`
          }
        })
      })
      .then((userRes) => {
        // 사용자 정보 저장
        const userId = userRes.data.username
        userKey.value = userId
        currentUser.value = userRes.data
        router.push({ 
          name: 'calender', 
          params: { userName: userId }
        })
      })
      .catch((err) => {
        console.log(err)
        alert('로그인에 실패했습니다.')
      })
  }
  const logOut = async () => {
    try {
      await axios({
        method: 'post',
        url: `${API_URL}/api/auth/logout/`,
        headers: {
          Authorization: `Token ${token.value}`
        }
      })

      sessionStorage.clear()
      token.value = null
      currentUser.value = null
      router.push('/')
    } catch (error) {
      console.error('로그아웃 실패:', error)
      sessionStorage.clear()
      token.value = null
      currentUser.value = null
      router.push('/')
    }
  }
 
  const getCurrentPosition = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by this browser.'))
      }
      
      navigator.geolocation.getCurrentPosition(
        position => resolve(position),
        error => reject(error),
        { enableHighAccuracy: true }
      )
    })
  }

  const kakaoLogin = () => {
    const REST_API_KEY = import.meta.env.VITE_KAKAO_API_KEY;
    const REDIRECT_URI = import.meta.env.VITE_KAKAO_REDIRECT_URI;
    const KAKAO_AUTH_URL = `https://kauth.kakao.com/oauth/authorize?response_type=code&client_id=${REST_API_KEY}&redirect_uri=${REDIRECT_URI}&prompt=login`;
    
    window.location.href = KAKAO_AUTH_URL;
  };

  const handleKakaoCallback = async (code) => {
    try {
      // 백엔드에 인증 코드 전송
      const response = await axios.get(`${API_URL}/api/v1/accounts/kakao/callback/`, {
        params: { code: code }
      });
  
      if (response.data) {
        // 사용자 정보 저장
        userKey.value = response.data.username;
        currentUser.value = response.data;
  
        // 위치 정보 가져오기
        try {
          const position = await getCurrentPosition();
          userLocation.value = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          };
        } catch (error) {
          console.error('위치 정보 가져오기 실패:', error);
        }
  
        router.push({ 
          name: 'calender', 
          params: { userName: response.data.username }
        });
      }
    } catch (error) {
      console.error('카카오 로그인 처리 실패:', error);
      alert('카카오 로그인에 실패했습니다.');
      router.push('/login');
    }
  };
 
  
  return {  userKey,
    currentUser,
    logOut,
    API_URL,
    signUp,
    logIn,
    token,
    userLocation,
    kakaoLogin,
    handleKakaoCallback }
}, {persist : {
  storage: sessionStorage
}})
