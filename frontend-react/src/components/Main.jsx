import React from 'react'
import Button from './Button'

const Main = () => {
  return (
    <>
    <div className="container">
        <div className="p-5 text-center bg-light-dark rounded">
            <h1 className='text-light'>Stock Prediction Portal</h1>
            <p className="text-light lead">Lorem ipsum dolor sit, amet consectetur adipisicing elit. Odit temporibus quo sint quia iusto quod in. Magni maiores eum aliquid voluptates facere ut dolorem nihil adipisci quasi distinctio sapiente laborum libero exercitationem, facilis quae suscipit aut, ducimus quas molestias sit soluta necessitatibus iure recusandae. Nam.</p>
            <Button text="Explore Now" class="btn-info" url="/dashboard"/>
        </div>
    </div>
    </>
  )
}

export default Main